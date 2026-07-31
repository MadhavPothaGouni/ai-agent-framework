from app.agents.code_extraction import extract_code_block


def test_extracts_code_from_fenced_python_block():
    text = "Here you go:\n```python\ndef add(a, b):\n    return a + b\n```\nHope that helps!"
    result = extract_code_block(text)
    assert result == "def add(a, b):\n    return a + b\n"


def test_extracts_code_from_fence_with_no_language_tag():
    text = "```\nx = 1\n```"
    result = extract_code_block(text)
    assert result == "x = 1\n"


def test_returns_plain_text_unchanged_when_no_fence_present():
    text = "def add(a, b):\n    return a + b"
    result = extract_code_block(text)
    assert result == "def add(a, b):\n    return a + b\n"


def test_handles_empty_string():
    assert extract_code_block("") == ""