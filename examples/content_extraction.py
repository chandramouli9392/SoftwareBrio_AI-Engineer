"""Content extraction example for DAVE."""

from __future__ import annotations

import asyncio

from pydantic import BaseModel

from dave import DaveConfig, DaveEngine


class ArticleSummary(BaseModel):
    title: str
    description: str
    key_points: list[str]


async def main() -> None:
    engine = DaveEngine(config=DaveConfig.from_env())
    result = await engine.extract(
        "https://example.com",
        ArticleSummary,
        prompt="Extract the article title, description, and key points.",
        include_metadata=True,
    )
    print(engine.to_json(result))


if __name__ == "__main__":
    asyncio.run(main())
