from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from sleep_agent.schemas import KnowledgeChunk


def load_chunks(knowledge_dir: Path) -> list[KnowledgeChunk]:
    sources = {item["source_id"]: item for item in json.loads(
        (knowledge_dir / "sources.json").read_text(encoding="utf-8")
    )}
    chunks: list[KnowledgeChunk] = []
    for path in sorted((knowledge_dir / "documents").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        source_match = re.search(r"^source_id:\s*(\S+)", text, re.MULTILINE)
        if not source_match or source_match.group(1) not in sources:
            raise ValueError(f"missing or unknown source_id in {path.name}")
        source = sources[source_match.group(1)]
        sections = re.split(r"(?m)^##\s+", text)
        for part in sections[1:]:
            lines = part.strip().splitlines()
            section = lines[0].strip()
            body = "\n".join(lines[1:]).strip()
            if not body:
                continue
            digest = hashlib.sha256(f"{path.name}:{section}:{body}".encode()).hexdigest()
            chunks.append(KnowledgeChunk(
                chunk_id=digest[:16], text=body, source_id=source["source_id"],
                source_title=source["title"], source_url=source["url"], section=section,
            ))
    return chunks

