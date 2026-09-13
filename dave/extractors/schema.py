"""Schema adaptation and validation utilities."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, TypeVar

from pydantic import BaseModel, create_model
from pydantic import ValidationError as PydanticValidationError

from dave.core.errors import ValidationError

T = TypeVar("T", bound=BaseModel)

ZERO_CONFIG_PROMPT = (
    "Auto-detect the most important structured data on this page. "
    "Return a compact object with page_type, title, summary, key_entities, key_facts, links, contacts, prices, "
    "products, jobs, and calls_to_action when present. Prefer useful developer-ready field names."
)


@dataclass(slots=True)
class SchemaAdapter:
    """Wraps a Pydantic model or prompt into a consistent schema object."""

    model: type[BaseModel] | None
    prompt: str
    zero_config: bool = False

    @property
    def has_model(self) -> bool:
        """Return whether this adapter has a concrete Pydantic model."""
        return self.model is not None

    @property
    def json_schema(self) -> dict[str, Any]:
        """Return a JSON schema for LLM constrained output."""
        if self.model is not None:
            return self.model.model_json_schema()
        return create_model("DaveSmartExtraction", data=(dict[str, Any], ...)).model_json_schema()


def make_schema_adapter(schema_or_prompt: type[T] | str | None = None, prompt: str | None = None) -> SchemaAdapter:
    """Normalize user input into a schema adapter."""
    if schema_or_prompt is None:
        return SchemaAdapter(model=None, prompt=prompt or ZERO_CONFIG_PROMPT, zero_config=True)
    if isinstance(schema_or_prompt, str):
        return SchemaAdapter(model=None, prompt=schema_or_prompt)
    if not isinstance(schema_or_prompt, type) or not issubclass(schema_or_prompt, BaseModel):
        raise TypeError("schema_or_prompt must be a Pydantic BaseModel class, prompt string, or None")
    return SchemaAdapter(model=schema_or_prompt, prompt=prompt or f"Extract data matching {schema_or_prompt.__name__}.")


def validate_against_schema(data: dict[str, Any], schema: type[T] | None) -> T | dict[str, Any]:
    """Validate extracted data against a Pydantic schema when supplied."""
    if schema is None:
        return data
    try:
        return schema.model_validate(data)
    except PydanticValidationError as exc:
        raise ValidationError(str(exc)) from exc


def schema_prompt(adapter: SchemaAdapter) -> str:
    """Build a compact schema instruction for an LLM."""
    schema_json = json.dumps(adapter.json_schema, indent=2, sort_keys=True)
    return (
        "Return only valid JSON that matches this JSON Schema. "
        "Do not include markdown fences or commentary.\n"
        f"Schema:\n{schema_json}"
    )
