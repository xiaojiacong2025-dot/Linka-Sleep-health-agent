from __future__ import annotations

from typing import Any


def filter_valid_evidence(items: list[dict[str, Any]], allowed_ids: set[str]) -> list[dict[str, Any]]:
    return [item for item in items if str(item.get("id", item.get("chunk_id", ""))) in allowed_ids]


def validate_citations(citations: list[dict[str, str]], allowed_ids: set[str]) -> list[dict[str, str]]:
    return [citation for citation in citations if citation.get("chunk_id") in allowed_ids]

