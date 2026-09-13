"""Confidence scoring for extracted values."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class FieldConfidence:
    """Confidence for one extracted field."""

    field: str
    score: float
    evidence: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class ConfidenceReport:
    """Aggregated confidence for an extraction."""

    overall: float
    fields: list[FieldConfidence]

    def as_dict(self) -> dict[str, Any]:
        """Serialize confidence data."""
        return {
            "overall": self.overall,
            "fields": [field.__dict__ for field in self.fields],
        }


def _flatten(data: dict[str, Any], prefix: str = "") -> list[tuple[str, Any]]:
    values: list[tuple[str, Any]] = []
    for key, value in data.items():
        name = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            values.extend(_flatten(value, name))
        else:
            values.append((name, value))
    return values


def score_confidence(data: dict[str, Any], source_text: str, evidence: dict[str, str] | None = None) -> ConfidenceReport:
    """Score confidence using evidence presence, value completeness, and source overlap."""
    flattened = _flatten(data)
    if not flattened:
        return ConfidenceReport(overall=0.0, fields=[])

    lower_source = source_text.lower()
    field_scores: list[FieldConfidence] = []
    for field, value in flattened:
        value_text = "" if value is None else str(value).strip()
        if not value_text:
            score = 0.15
            reason = "empty value"
        elif evidence and field in evidence:
            score = 0.9 if evidence[field].lower() in lower_source else 0.72
            reason = "evidence supplied"
        elif len(value_text) > 2 and value_text.lower() in lower_source:
            score = 0.82
            reason = "value appears in source text"
        elif isinstance(value, (int, float, bool)):
            score = 0.72
            reason = "typed scalar value"
        else:
            score = 0.58
            reason = "value inferred without direct overlap"
        field_scores.append(FieldConfidence(field=field, score=round(score, 3), evidence=(evidence or {}).get(field), reason=reason))

    overall = round(sum(field.score for field in field_scores) / len(field_scores), 3)
    return ConfidenceReport(overall=overall, fields=field_scores)
