from __future__ import annotations

from sleep_agent.rag.index import rebuild_index
from sleep_agent.rag.ingest import load_chunks
from sleep_agent.rag.retriever import retrieve
from sleep_agent.settings import load_settings
from sleep_agent.storage.database import initialize_database


def main() -> None:
    settings = load_settings()
    initialize_database(settings.database_path)
    chunks = load_chunks(settings.project_root / "knowledge")
    count = rebuild_index(settings.database_path, chunks)
    sample = retrieve(settings.database_path, "RMSSD 是什么", top_k=2)
    print({"chunks": count, "sample_results": [item.chunk_id for item in sample]})


if __name__ == "__main__":
    main()

