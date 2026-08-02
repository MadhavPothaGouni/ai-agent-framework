from app.core.pricing import cost_for


def test_mock_provider_is_always_free():
    assert cost_for("mock", input_tokens=1_000_000, output_tokens=1_000_000) == 0.0


def test_known_provider_uses_its_own_rate():
    # anthropic: $3/1M input, $15/1M output (see app/core/pricing.py)
    cost = cost_for("anthropic", input_tokens=1_000_000, output_tokens=1_000_000)
    assert cost == 18.0


def test_cost_scales_linearly_with_tokens():
    half = cost_for("openai", input_tokens=500_000, output_tokens=0)
    full = cost_for("openai", input_tokens=1_000_000, output_tokens=0)
    assert round(full, 6) == round(half * 2, 6)


def test_unknown_provider_falls_back_to_default_rate_instead_of_zero():
    cost = cost_for("some-custom-plugin-provider", input_tokens=1_000_000, output_tokens=0)
    assert cost > 0


def test_zero_tokens_costs_nothing():
    assert cost_for("anthropic", input_tokens=0, output_tokens=0) == 0.0