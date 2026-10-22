"""
==============================================================================
File: backend/app/services/llm/cost.py
Purpose: Accurate token tracking and USD cost computation for LLM invocations.
Architecture: Backend Services / Telemetry & Cost Engine
==============================================================================

Cost Visibility as a First-Class Citizen:
Enterprise AI deployments frequently stall because leaders lack visibility into
per-run inference costs. By calculating input and output token expenditures down to
fractional cents, the Insurance Requirements Agent provides real-time ROI tracking
and ensures generation budgets are never exceeded.
"""

from typing import Dict, Tuple

# Official Google GenAI & Gemini pricing per 1,000,000 tokens (USD)
# (Input Price / 1M tokens, Output Price / 1M tokens)
MODEL_PRICING: Dict[str, Tuple[float, float]] = {
    # Gemini 2.5 Flash / 1.5 Flash (Standard Workhorse)
    "gemini-2.5-flash": (0.075, 0.30),
    "gemini-1.5-flash": (0.075, 0.30),
    "gemini-1.5-flash-8b": (0.0375, 0.15),
    # Gemini 1.5 Pro (Deep Reasoning)
    "gemini-1.5-pro": (3.50, 10.50),
    # Default fallback
    "default": (0.10, 0.40),
}


def calculate_cost(model_name: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Computes the estimated cost in USD for a given token usage and model name.

    Args:
        model_name: The identifier of the model (e.g., 'gemini-2.5-flash').
        prompt_tokens: Number of prompt / input tokens.
        completion_tokens: Number of completion / output tokens.

    Returns:
        float: Total USD cost rounded to 6 decimal places.
    """
    normalized_name = model_name.lower().strip()
    price_tuple = MODEL_PRICING.get(normalized_name)
    
    # Prefix match if model name has sub-version tags (e.g. 'gemini-2.5-flash-001')
    if not price_tuple:
        for k, v in MODEL_PRICING.items():
            if k in normalized_name:
                price_tuple = v
                break

    if not price_tuple:
        price_tuple = MODEL_PRICING["default"]

    input_cost_per_m, output_cost_per_m = price_tuple
    total_cost = (prompt_tokens * (input_cost_per_m / 1_000_000.0)) + (
        completion_tokens * (output_cost_per_m / 1_000_000.0)
    )
    return round(total_cost, 6)
