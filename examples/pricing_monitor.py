"""Pricing monitoring example for DAVE."""

from __future__ import annotations

import asyncio

from pydantic import BaseModel, Field

from dave import DaveConfig, DaveEngine


class PricingSnapshot(BaseModel):
    plan_name: str = Field(description="Primary plan name")
    price: str = Field(description="Displayed price")
    billing_period: str | None = Field(default=None, description="Billing period")


async def main() -> None:
    engine = DaveEngine(config=DaveConfig.from_env())
    previous = {"plan_name": "Starter", "price": "$19", "billing_period": "month"}
    current = await engine.extract(
        "https://example.com/pricing",
        PricingSnapshot,
        prompt="Extract the most prominent pricing plan.",
    )
    print(DaveEngine.diff(previous, current.model_dump()))


if __name__ == "__main__":
    asyncio.run(main())
