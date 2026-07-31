import re

_FENCE_RE = re.compile(r"```(?:\w+)?\n(.*?)```", re.DOTALL)


def extract_code_block(text: str) -> str:
    match = _FENCE_RE.search(text)
    body = match.group(1) if match else text
    body = body.strip()
    return f"{body}\n" if body else body