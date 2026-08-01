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