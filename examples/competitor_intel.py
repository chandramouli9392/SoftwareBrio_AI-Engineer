"""Competitor intelligence example for DAVE."""

from __future__ import annotations

import asyncio

from dave import DaveConfig, DaveEngine


async def main() -> None:
    engine = DaveEngine(config=DaveConfig.from_env())
    result = await engine.extract(
        "https://example.com",
        "Summarize the product positioning, target audience, and differentiators.",
        include_metadata=True,
    )
    print(engine.to_json(result))


if __name__ == "__main__":
    asyncio.run(main())
