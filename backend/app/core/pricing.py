# provider name -> (input $ / 1M tokens, output $ / 1M tokens)
PRICING_PER_MILLION_TOKENS: dict[str, tuple[float, float]] = {
    "mock": (0.0, 0.0),
    "anthropic": (3.00, 15.00),  # Claude Sonnet-class pricing
    "openai": (2.00, 8.00),      # GPT-4.1-class pricing
    "gemini": (0.30, 2.50),      # Gemini Flash-class pricing
}

# Fallback for any provider name not in the table above (e.g. a custom
# plugin provider) — a mid-tier rate so cost tracking degrades gracefully
# instead of silently reporting $0.
DEFAULT_RATE = (3.00, 15.00)


def cost_for(provider: str, input_tokens: int, output_tokens: int) -> float:
    """Returns the USD cost of one completion given its token counts."""
    input_rate, output_rate = PRICING_PER_MILLION_TOKENS.get(provider, DEFAULT_RATE)
    cost = (input_tokens / 1_000_000) * input_rate + (output_tokens / 1_000_000) * output_rate
    return round(cost, 8)