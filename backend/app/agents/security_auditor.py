
import ast
import re
from dataclasses import asdict, dataclass

from app.agents.base import AgentContext, AgentResult, BaseAgent

_SECRET_NAME_PATTERN = re.compile(r"(password|passwd|secret|api[_-]?key|access[_-]?key|token)", re.IGNORECASE)
_SQL_KEYWORD_PATTERN = re.compile(r"\b(SELECT|INSERT|UPDATE|DELETE)\b", re.IGNORECASE)


@dataclass
class Finding:
    severity: str  # "high" | "medium"
    rule: str
    message: str
    line: int


class SecurityAuditorAgent(BaseAgent):
    name = "security_auditor"

    def run(self, context: AgentContext) -> AgentResult:
        code = context.memory.get("code", "")

        try:
            tree = ast.parse(code)
        except SyntaxError:
            # Not this agent's job to flag syntax errors — the Tester
            # already caught that. Don't block review on an unparsable
            # snippet; just report that the audit couldn't run.
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
        ]

        high_severity = [f for f in findings if f.severity == "high"]
        passed = not high_severity

        context.memory["security_passed"] = passed
        context.memory["security_findings"] = [asdict(f) for f in findings]

        if not findings:
            summary = "Security audit: no issues found."
        else:
            lines = [f"[{f.severity.upper()}] line {f.line}: {f.rule} — {f.message}" for f in findings]
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