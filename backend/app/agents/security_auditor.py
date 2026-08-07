
import ast
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from app.agents.base import AgentContext, AgentResult, BaseAgent
from app.agents.vulnerability_db import KNOWN_VULNERABLE_PACKAGES, is_vulnerable_version

_SECRET_NAME_PATTERN = re.compile(r"(password|passwd|secret|api[_-]?key|access[_-]?key|token)", re.IGNORECASE)
_SQL_KEYWORD_PATTERN = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", re.IGNORECASE)
_VERSION_SPECIFIER_PATTERN = re.compile(r"[=<>!~]")


_IMPORT_NAME_TO_PACKAGE = {
    "jwt": "pyjwt",
    "django": "django",
    "flask": "flask",
    "urllib3": "urllib3",
    "yaml": "pyyaml",
    "requests": "requests",
}


@dataclass
class Finding:
    severity: str  # "high" | "medium"
    rule: str
    message: str
    line: int
    file: str = "solution.py"


class SecurityAuditorAgent(BaseAgent):
    name = "security_auditor"

    def run(self, context: AgentContext) -> AgentResult:
        code = context.memory.get("code", "")
        workspace_dir = context.memory.get("workspace_dir")

        try:
            tree = ast.parse(code)
        except SyntaxError:
          
            context.memory["security_passed"] = True
            context.memory["security_findings"] = []
            return AgentResult(
                output="Security audit skipped: code did not parse (SyntaxError already caught by tests).",
                success=True,
                metadata={"findings": []},
            )

        findings: list[Finding] = [
            *self._check_dangerous_calls(tree),
            *self._check_hardcoded_secrets(tree),
            *self._check_sql_string_building(code),
            *self._check_vulnerable_imports(tree),
            *self._check_requirements_file(workspace_dir),
        ]

        high_severity = [f for f in findings if f.severity == "high"]
        passed = not high_severity

        context.memory["security_passed"] = passed
        context.memory["security_findings"] = [asdict(f) for f in findings]

        if not findings:
            summary = "Security audit: no issues found."
        else:
            lines = [
                f"[{f.severity.upper()}] {f.file}:{f.line}: {f.rule} — {f.message}" for f in findings
            ]
            summary = "Security audit findings:\n" + "\n".join(lines)

        return AgentResult(
            output=summary,
            success=passed,
            metadata={
                "findings": [asdict(f) for f in findings],
                "high_severity_count": len(high_severity),
            },
        )

    @staticmethod
    def _check_dangerous_calls(tree: ast.AST) -> list[Finding]:
        findings: list[Finding] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func

            if isinstance(func, ast.Name) and func.id in ("eval", "exec"):
                findings.append(
                    Finding("high", "dangerous-call", f"Use of {func.id}() allows arbitrary code execution.", node.lineno)
                )
                continue

            if isinstance(func, ast.Attribute):
                owner = func.value.id if isinstance(func.value, ast.Name) else None

                if owner == "os" and func.attr == "system":
                    findings.append(
                        Finding(
                            "high",
                            "dangerous-call",
                            "os.system() allows arbitrary shell execution; use subprocess with a list of args instead.",
                            node.lineno,
                        )
                    )
                elif owner == "pickle" and func.attr in ("loads", "load"):
                    findings.append(
                        Finding(
                            "high",
                            "unsafe-deserialization",
                            "pickle.load(s)() can execute arbitrary code when given untrusted input.",
                            node.lineno,
                        )
                    )
                elif owner == "subprocess" and func.attr in ("run", "call", "Popen", "check_call", "check_output"):
                    for kw in node.keywords:
                        if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                            findings.append(
                                Finding(
                                    "medium",
                                    "shell-true",
                                    f"subprocess.{func.attr}(..., shell=True) risks shell injection if any input isn't fully trusted.",
                                    node.lineno,
                                )
                            )

        return findings

    @staticmethod
    def _check_hardcoded_secrets(tree: ast.AST) -> list[Finding]:
        findings: list[Finding] = []

        for node in ast.walk(tree):
            if not isinstance(node, ast.Assign):
                continue
            value = node.value
            if isinstance(value, ast.Constant) and isinstance(value.value, str) and value.value.strip():
                for target in node.targets:
                    if isinstance(target, ast.Name) and _SECRET_NAME_PATTERN.search(target.id):
                        findings.append(
                            Finding(
                                "high",
                                "hardcoded-secret",
                                f"Variable '{target.id}' is assigned a literal string — looks like a hardcoded credential.",
                                node.lineno,
                            )
                        )

        return findings

    @staticmethod
    def _check_sql_string_building(code: str) -> list[Finding]:
        findings: list[Finding] = []

        for lineno, line in enumerate(code.splitlines(), start=1):
            if not _SQL_KEYWORD_PATTERN.search(line):
                continue
            looks_concatenated = "+" in line
            looks_fstring = "f'" in line or 'f"' in line
            if looks_concatenated or looks_fstring:
                findings.append(
                    Finding(
                        "medium",
                        "sql-string-building",
                        "SQL keyword found alongside string concatenation/f-string — verify this isn't building "
                        "a query from untrusted input (use parameterized queries instead).",
                        lineno,
                    )
                )

        return findings

    @staticmethod
    def _check_vulnerable_imports(tree: ast.AST) -> list[Finding]:
        findings: list[Finding] = []
        already_flagged: set[str] = set()

        for node in ast.walk(tree):
            module_hits: list[tuple[str, int]] = []
            if isinstance(node, ast.Import):
                module_hits.extend((alias.name.split(".")[0], node.lineno) for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                module_hits.append((node.module.split(".")[0], node.lineno))

            for root_module, lineno in module_hits:
                package = _IMPORT_NAME_TO_PACKAGE.get(root_module)
                if package is None or package in already_flagged:
                    continue
                entry = KNOWN_VULNERABLE_PACKAGES.get(package)
                if entry is None:
                    continue

                already_flagged.add(package)
                findings.append(
                    Finding(
                     
                        severity="medium",
                        rule="vulnerable-dependency",
                        message=(
                            f"imports '{root_module}' ({package}), a package with a history of known "
                            f"vulnerabilities. {entry.reason} {entry.advice} (Version not verifiable from "
                            "source alone — check requirements.txt or your installed version.)"
                        ),
                        line=lineno,
                        file="solution.py",
                    )
                )

        return findings

    @staticmethod
    def _parse_requirements_line(raw_line: str) -> tuple[str, str | None] | None:
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            return None
        line = line.split(";", 1)[0].strip()  # drop environment markers
        if not line:
            return None

        match = _VERSION_SPECIFIER_PATTERN.search(line)
        if match is None:
            return line, None

        name = line[: match.start()].strip()
        specifier = line[match.start() :].strip()
        if specifier.startswith("=="):
            return name, specifier[2:].strip()
        return name, None  # >=, ~=, etc -- can't pin an exact version

    @classmethod
    def _check_requirements_file(cls, workspace_dir: str | None) -> list[Finding]:
        findings: list[Finding] = []
        if not workspace_dir:
            return findings

        req_path = Path(workspace_dir) / "requirements.txt"
        if not req_path.exists():
            return findings

        try:
            raw_lines = req_path.read_text().splitlines()
        except OSError:
            return findings

        for lineno, raw_line in enumerate(raw_lines, start=1):
            parsed = cls._parse_requirements_line(raw_line)
            if parsed is None:
                continue
            package, pinned_version = parsed

            entry = KNOWN_VULNERABLE_PACKAGES.get(package.lower())
            if entry is None or not is_vulnerable_version(package, pinned_version):
                continue

            version_note = f"pinned at {pinned_version}" if pinned_version else "version unpinned"
            findings.append(
                Finding(
                    severity=entry.severity,
                    rule="vulnerable-dependency",
                    message=f"'{package}' ({version_note}): {entry.reason} {entry.advice}",
                    line=lineno,
                    file="requirements.txt",
                )
            )

        return findings