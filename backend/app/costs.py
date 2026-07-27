"""Token → money conversion for the cost dashboard."""
import os

# USD per million tokens (input, output) — Anthropic API list prices
PRICING_USD_PER_MTOK = {
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-sonnet-5": (3.00, 15.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "gpt-4o": (2.50, 10.00),
    "gemini-2.0-flash": (0.10, 0.40),
}

USD_TO_INR = float(os.getenv("USD_TO_INR", "88"))


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    inp, out = PRICING_USD_PER_MTOK.get(model, (5.00, 25.00))
    return (input_tokens * inp + output_tokens * out) / 1_000_000


def cost_inr(model: str, input_tokens: int, output_tokens: int) -> float:
    return cost_usd(model, input_tokens, output_tokens) * USD_TO_INR
