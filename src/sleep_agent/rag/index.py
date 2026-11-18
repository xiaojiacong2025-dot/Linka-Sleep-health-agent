from __future__ import annotations

import hashlib
import re
from pathlib import Path

from sleep_agent.schemas import KnowledgeChunk
from sleep_agent.storage.database import connect


def char_tokens(text: str) -> str:
    compact = re.sub(r"\s+", "", text.lower())
    cjk = [compact[i:i + 2] for i in range(max(0, len(compact) - 1))
           if any("\u4e00" <= ch <= "\u9fff" for ch in compact[i:i + 2])]
    latin = re.findall(r"[a-z0-9_]{2,}", text.lower())
    return " ".join(dict.fromkeys(cjk + latin))


def rebuild_index(database_path: Path, chunks: list[KnowledgeChunk]) -> int:
    with connect(database_path) as db:
        db.execute("DELETE FROM knowledge_fts")
        db.execute("DELETE FROM knowledge_chunks")
        for chunk in chunks:
            search_text = char_tokens(chunk.text + " " + chunk.section)
            content_hash = hashlib.sha256(chunk.text.encode()).hexdigest()
            db.execute("INSERT INTO knowledge_chunks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (chunk.chunk_id, chunk.text, search_text, chunk.source_id,
                        chunk.source_title, chunk.source_url, chunk.section, content_hash))
            db.execute("INSERT INTO knowledge_fts(chunk_id, search_text) VALUES (?, ?)",
                       (chunk.chunk_id, search_text))
    return len(chunks)

