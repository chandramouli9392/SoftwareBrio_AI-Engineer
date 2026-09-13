from __future__ import annotations

import pytest

from dave import plugins, recipes
from dave.core.config import DaveConfig, LLMConfig
from dave.core.engine import DaveEngine
from dave.fetchers.base import BaseFetcher, FetchRequest, FetchResult


class RichFakeFetcher(BaseFetcher):
    async def fetch(self, request: FetchRequest) -> FetchResult:
        html = """
        <html>
          <head>
            <title>Acme AI</title>
            <meta name="description" content="Acme AI helps revenue teams find qualified accounts.">
          </head>
          <body>
            <h1>Acme AI</h1>
            <p>Pricing starts at $49 per month. Contact sales for enterprise.</p>
            <p>Email hello@acme.example for a demo.</p>
            <a href="https://acme.example/pricing">Pricing</a>
            <p>We are hiring a Remote Platform Engineer.</p>
          </body>
        </html>
        """
        text = "Acme AI. Pricing starts at $49 per month. Contact sales. Email hello@acme.example. Remote Platform Engineer."
        return FetchResult(
            url=request.url,
            final_url=request.url,
            status_code=200,
            headers={},
            html=html,
            text=text,
            elapsed_seconds=0.01,
            fetcher="rich_fake",
        )


def make_engine(tmp_path):
    config = DaveConfig(
        fetcher="http",
        cache={"enabled": True, "directory": tmp_path, "ttl_seconds": 60},
        llm=LLMConfig(provider="mock", model="mock"),
        min_confidence=0.5,
        retries=0,
        antibot={"min_delay_seconds": 0, "max_delay_seconds": 0},
    )
    return DaveEngine(config=config, fetchers={"http": RichFakeFetcher()})


@pytest.mark.asyncio
async def test_zero_config_extracts_intelligent_structure(tmp_path):
    engine = make_engine(tmp_path)

    result = await engine.extract("https://acme.example")

    assert result["title"] == "Acme AI"
    assert result["page_type"] in {"pricing", "careers", "contact", "company_or_content"}
    assert "hello@acme.example" in result["contacts"]["emails"]
    assert "$49" in result["prices"]


@pytest.mark.asyncio
async def test_stream_extract_emits_field_and_complete_events(tmp_path):
    engine = make_engine(tmp_path)

    events = [event async for event in engine.stream_extract("https://acme.example")]

    assert events[0].type == "fetch_started"
    assert any(event.type == "cost_estimated" for event in events)
    assert any(event.type == "field" and event.data.get("field") == "title" for event in events)
    assert events[-1].type == "complete"


def test_recipe_registry_returns_typed_schema():
    schema, prompt = recipes.get_recipe("company_info")

    assert schema is recipes.CompanyInfo
    assert "company intelligence" in prompt.lower()
    assert set(recipes.RECIPES) == {
        "company_info",
        "pricing",
        "job_listings",
        "contact_info",
        "product_features",
        "reviews",
    }


def test_plugin_registry_registers_custom_fetcher():
    plugins.registry.clear()
    fetcher = RichFakeFetcher()

    plugins.register_fetcher("internal", fetcher)

    assert plugins.get_fetchers()["internal"] is fetcher
    plugins.registry.clear()


@pytest.mark.asyncio
async def test_cost_estimate_is_positive_and_serializable(tmp_path):
    engine = make_engine(tmp_path)

    estimate = await engine.estimate_cost("https://acme.example")

    assert estimate.total_tokens > 0
    assert estimate.cost_usd >= 0
    serialized = engine.to_json(estimate)
    assert "total_tokens" in serialized
