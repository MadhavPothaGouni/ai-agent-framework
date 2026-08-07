from app.agents.base import AgentContext
from app.agents.security_auditor import SecurityAuditorAgent


def _run(code: str):
    context = AgentContext(task="t")
    context.memory["code"] = code
    result = SecurityAuditorAgent().run(context)
    return context, result


def test_clean_code_has_no_findings():
    context, result = _run(
        "def solution(a: int, b: int) -> int:\n"
        "    return a + b\n"
    )
    assert result.success is True
    assert context.memory["security_passed"] is True
    assert context.memory["security_findings"] == []


def test_eval_call_is_flagged_high_and_blocks_approval():
    context, result = _run(
        "def solution(expr):\n"
        "    return eval(expr)\n"
    )
    assert result.success is False
    assert context.memory["security_passed"] is False
    rules = [f["rule"] for f in context.memory["security_findings"]]
    assert "dangerous-call" in rules
    assert result.metadata["high_severity_count"] >= 1


def test_exec_call_is_flagged_high():
    _, result = _run("exec('print(1)')\n")
    assert result.success is False


def test_os_system_call_is_flagged_high():
    context, result = _run(
        "import os\n"
        "def solution(cmd):\n"
        "    return os.system(cmd)\n"
    )
    assert result.success is False
    rules = [f["rule"] for f in context.memory["security_findings"]]
    assert "dangerous-call" in rules


def test_pickle_loads_is_flagged_high():
    context, result = _run(
        "import pickle\n"
        "def solution(data):\n"
        "    return pickle.loads(data)\n"
    )
    assert result.success is False
    rules = [f["rule"] for f in context.memory["security_findings"]]
    assert "unsafe-deserialization" in rules


def test_hardcoded_secret_is_flagged_high():
    context, result = _run(
        "API_KEY = 'sk-super-secret-value-123'\n"
        "def solution():\n"
        "    return API_KEY\n"
    )
    assert result.success is False
    rules = [f["rule"] for f in context.memory["security_findings"]]
    assert "hardcoded-secret" in rules


def test_subprocess_shell_true_is_medium_and_does_not_block_approval():
    context, result = _run(
        "import subprocess\n"
        "def solution(cmd):\n"
        "    return subprocess.run(cmd, shell=True)\n"
    )
    # Medium severity alone shouldn't fail the audit.
    assert result.success is True
    assert context.memory["security_passed"] is True
    rules = [f["rule"] for f in context.memory["security_findings"]]
    assert "shell-true" in rules


def test_sql_string_concatenation_is_flagged_medium():
    context, result = _run(
        "def solution(user_id):\n"
        "    query = \"SELECT * FROM users WHERE id = \" + user_id\n"
        "    return query\n"
    )
    assert result.success is True  # medium only
    rules = [f["rule"] for f in context.memory["security_findings"]]
    assert "sql-string-building" in rules


def test_unparsable_code_does_not_crash_the_audit():
    context, result = _run("def solution(:\n    this is not valid python\n")
    assert result.success is True
    assert context.memory["security_passed"] is True
    assert context.memory["security_findings"] == []



def test_import_of_known_vulnerable_package_is_flagged_advisory_medium():
    context, result = _run(
        "import jwt\n"
        "def solution(token):\n"
        "    return jwt.decode(token, 'secret', algorithms=['HS256'])\n"
    )
    
    assert result.success is True
    rules = [f["rule"] for f in context.memory["security_findings"]]
    assert "vulnerable-dependency" in rules
    dep_findings = [f for f in context.memory["security_findings"] if f["rule"] == "vulnerable-dependency"]
    assert dep_findings[0]["severity"] == "medium"
    assert dep_findings[0]["file"] == "solution.py"


def test_import_of_package_not_in_registry_is_not_flagged():
    context, result = _run(
        "import math\n"
        "def solution(x):\n"
        "    return math.sqrt(x)\n"
    )
    rules = [f["rule"] for f in context.memory["security_findings"]]
    assert "vulnerable-dependency" not in rules
    assert result.success is True


def test_same_vulnerable_import_is_only_flagged_once():
    context, _ = _run(
        "import jwt\n"
        "import jwt.api_jwt\n"
        "def solution(token):\n"
        "    return jwt.decode(token, 'secret', algorithms=['HS256'])\n"
    )
    dep_findings = [f for f in context.memory["security_findings"] if f["rule"] == "vulnerable-dependency"]
    assert len(dep_findings) == 1


def test_requirements_txt_with_old_pinned_vulnerable_package_is_flagged_at_real_severity(tmp_path):
    from app.agents.base import AgentContext
    from app.agents.security_auditor import SecurityAuditorAgent

    (tmp_path / "requirements.txt").write_text("pyjwt==2.0.0\nrequests==2.31.0\n")

    context = AgentContext(task="t")
    context.memory["code"] = "def solution(a, b):\n    return a + b\n"
    context.memory["workspace_dir"] = str(tmp_path)

    result = SecurityAuditorAgent().run(context)

    assert result.success is False  
    dep_findings = [f for f in context.memory["security_findings"] if f["rule"] == "vulnerable-dependency"]
    assert len(dep_findings) == 1  
    assert dep_findings[0]["file"] == "requirements.txt"
    assert dep_findings[0]["severity"] == "high"
    assert "pyjwt" in dep_findings[0]["message"]


def test_requirements_txt_with_unpinned_known_bad_package_is_flagged(tmp_path):
    from app.agents.base import AgentContext
    from app.agents.security_auditor import SecurityAuditorAgent

    (tmp_path / "requirements.txt").write_text("django>=3.0\n")

    context = AgentContext(task="t")
    context.memory["code"] = "def solution(a, b):\n    return a + b\n"
    context.memory["workspace_dir"] = str(tmp_path)

    result = SecurityAuditorAgent().run(context)

    dep_findings = [f for f in context.memory["security_findings"] if f["rule"] == "vulnerable-dependency"]
    assert len(dep_findings) == 1
    assert "unpinned" in dep_findings[0]["message"]


def test_requirements_txt_with_no_known_vulnerable_packages_is_clean(tmp_path):
    from app.agents.base import AgentContext
    from app.agents.security_auditor import SecurityAuditorAgent

    (tmp_path / "requirements.txt").write_text("numpy==1.26.0\npandas==2.2.0\n")

    context = AgentContext(task="t")
    context.memory["code"] = "def solution(a, b):\n    return a + b\n"
    context.memory["workspace_dir"] = str(tmp_path)

    result = SecurityAuditorAgent().run(context)

    assert result.success is True
    assert context.memory["security_findings"] == []


def test_missing_requirements_txt_is_a_no_op(tmp_path):
    from app.agents.base import AgentContext
    from app.agents.security_auditor import SecurityAuditorAgent

    context = AgentContext(task="t")
    context.memory["code"] = "def solution(a, b):\n    return a + b\n"
    context.memory["workspace_dir"] = str(tmp_path)  

    result = SecurityAuditorAgent().run(context)

    assert result.success is True
    assert context.memory["security_findings"] == []


def test_no_workspace_dir_is_a_no_op():
  
    context, result = _run("def solution(a, b):\n    return a + b\n")
    assert result.success is True
    assert context.memory["security_findings"] == []


def test_requirements_txt_comment_and_blank_lines_are_ignored(tmp_path):
    from app.agents.base import AgentContext
    from app.agents.security_auditor import SecurityAuditorAgent

    (tmp_path / "requirements.txt").write_text(
        "# core deps\n\npyjwt==2.4.0  # already patched\n\n-r other-requirements.txt\n"
    )

    context = AgentContext(task="t")
    context.memory["code"] = "def solution(a, b):\n    return a + b\n"
    context.memory["workspace_dir"] = str(tmp_path)

    result = SecurityAuditorAgent().run(context)

    assert result.success is True
    assert context.memory["security_findings"] == []