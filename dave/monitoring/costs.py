"""Token usage and cost tracking."""

from __future__ import annotations

from dataclasses import dataclass, field


def estimate_tokens(text: str) -> int:
    """Estimate token count using a conservative character heuristic."""
    return max(1, len(text) // 4)


@dataclass(frozen=True, slots=True)
class ModelPricing:
    """Pricing per one million input and output tokens."""

    input_per_million: float
    output_per_million: float


DEFAULT_PRICING = {
    ("openai", "gpt-4o-mini"): ModelPricing(input_per_million=0.15, output_per_million=0.60),
    ("openai", "gpt-4o"): ModelPricing(input_per_million=5.00, output_per_million=15.00),
    ("anthropic", "claude-3-5-sonnet-latest"): ModelPricing(input_per_million=3.00, output_per_million=15.00),
    ("groq", "qwen/qwen3.8-27b"): ModelPricing(input_per_million=0.35, output_per_million=0.50),
    ("groq", "openai/gpt-oss-120b"): ModelPricing(input_per_million=0.60, output_per_million=0.80),
    ("groq", "llama-3.3-70b-versatile"): ModelPricing(input_per_million=0.59, output_per_million=0.79),
    ("groq", "llama-3.1-8b-instant"): ModelPricing(input_per_million=0.05, output_per_million=0.08),
    ("ollama", "local"): ModelPricing(input_per_million=0.0, output_per_million=0.0),
    ("mock", "mock"): ModelPricing(input_per_million=0.0, output_per_million=0.0),
}


@dataclass(slots=True)
class CostTracker:
    """Accumulates token usage and estimated costs."""

    pricing: dict[tuple[str, str], ModelPricing] = field(default_factory=lambda: dict(DEFAULT_PRICING))
    total_cost_usd: float = 0.0
    total_tokens: int = 0

    def estimate_cost(self, provider: str, model: str, usage: dict[str, int]) -> float:
        """Estimate and accumulate provider cost from usage metadata."""
        pricing = self.pricing.get((provider, model)) or self.pricing.get((provider, "local"))
        if pricing is None:
            pricing = ModelPricing(input_per_million=1.0, output_per_million=3.0)
        prompt_tokens = int(usage.get("prompt_tokens", 0))
        completion_tokens = int(usage.get("completion_tokens", 0))
        cost = (
            prompt_tokens / 1_000_000 * pricing.input_per_million
            + completion_tokens / 1_000_000 * pricing.output_per_million
        )
        self.total_cost_usd += cost
        self.total_tokens += int(usage.get("total_tokens", prompt_tokens + completion_tokens))
        return round(cost, 8)
