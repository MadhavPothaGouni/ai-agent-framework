from app.core.token_counter import estimate_tokens


def test_empty_string_is_zero_tokens():
    assert estimate_tokens("") == 0


def test_nonempty_text_is_never_zero_tokens():
    assert estimate_tokens("hi") >= 1


def test_longer_text_estimates_more_tokens():
    short = estimate_tokens("a" * 40)
    long = estimate_tokens("a" * 400)
    assert long > short


def test_roughly_four_characters_per_token():
    text = "a" * 400
    assert estimate_tokens(text) == 100