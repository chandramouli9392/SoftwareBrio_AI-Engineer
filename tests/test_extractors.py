from __future__ import annotations

import pytest
from pydantic import BaseModel

from dave.core.config import DaveConfig, LLMConfig
from dave.extractors.confidence import score_confidence
from dave.extractors.llm import LLMExtractor
from dave.extractors.schema import make_schema_adapter


class Product(BaseModel):
    title: str
    description: str


@pytest.mark.asyncio
async def test_mock_extractor_validates_schema():
    config = DaveConfig(llm=LLMConfig(provider="mock", model="mock"), min_confidence=0.5)
    extractor = LLMExtractor(config)
    adapter = make_schema_adapter(Product)

    result = await extractor.extract("<title>Widget</title> Description: A useful widget.", adapter)

    assert result.data["title"] == "Widget"
    assert result.confidence.overall >= 0.5


def test_confidence_scores_direct_evidence():
    report = score_confidence({"title": "Widget"}, "The product is Widget", evidence={"title": "Widget"})
    assert report.overall >= 0.8
    assert report.fields[0].field == "title"
