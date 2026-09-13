"""Lead research example for DAVE."""

from __future__ import annotations

import asyncio

from pydantic import BaseModel, Field

from dave import DaveConfig, DaveEngine


class CompanyLead(BaseModel):
    name: str = Field(description="Company name")
    description: str = Field(description="Short company description")
    contact_page: str | None = Field(default=None, description="Contact or sales page")


async def main() -> None:
    engine = DaveEngine(config=DaveConfig.from_env())
    result = await engine.extract(
        "https://example.com",
        CompanyLead,
        prompt="Extract lead research details for sales outreach.",
        include_metadata=True,
    )
    print(engine.to_json(result))


if __name__ == "__main__":
    asyncio.run(main())
