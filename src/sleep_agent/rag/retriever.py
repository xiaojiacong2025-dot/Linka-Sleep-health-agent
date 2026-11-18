from __future__ import annotations

from pathlib import Path

from sleep_agent.rag.index import char_tokens
from sleep_agent.schemas import KnowledgeChunk
from sleep_agent.storage.database import connect


def retrieve(database_path: Path, query: str, top_k: int = 4) -> list[KnowledgeChunk]:
    tokens = char_tokens(query).split()
    if not tokens:
        return []
    expression = " OR ".join(f'"{token}"' for token in tokens[:30])
    with connect(database_path) as db:
        rows = db.execute(
            """SELECT k.*, bm25(knowledge_fts) AS score FROM knowledge_fts
            JOIN knowledge_chunks k ON k.chunk_id=knowledge_fts.chunk_id
            WHERE knowledge_fts MATCH ? ORDER BY score LIMIT ?""", (expression, min(top_k, 10))
        ).fetchall()
    return [KnowledgeChunk(
        chunk_id=row["chunk_id"], text=row["text"], source_id=row["source_id"],
        source_title=row["source_title"], source_url=row["source_url"],
        section=row["section"], rank=float(row["score"]),
    ) for row in rows]
