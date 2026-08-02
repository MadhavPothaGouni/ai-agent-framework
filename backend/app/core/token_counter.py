
_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    """Rough token count for `text`. Never returns 0 for non-empty input,
    so even a one-word prompt registers a nonzero (if tiny) cost.
    """
    if not text:
        return 0
    return max(1, len(text) // _CHARS_PER_TOKEN)