"""Build the ChromaDB vector store from the SciFact corpus. Owner: Member 2.

Usage:
    python scripts/ingest.py            # full ingest (default)
    python scripts/ingest.py --limit 100  # ingest first 100 docs (dev/debug)

Steps:
    1. Download the SciFact corpus from HuggingFace (allenai/scifact).
    2. Convert each document into a passage (join abstract sentences).
    3. Embed all passages with sentence-transformers.
    4. Upsert into ChromaDB with stable document IDs.
    5. Optionally save processed passages to data/processed/passages.jsonl.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path so ``src.*`` imports work when
# running the script directly with ``python scripts/ingest.py``.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_settings  # noqa: E402
from src.logging_setup import configure_logging, get_logger  # noqa: E402
from src.rag.embeddings import Embedder  # noqa: E402
from src.rag.store import get_collection  # noqa: E402

configure_logging()
log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
BATCH_SIZE = 256  # ChromaDB upsert batch size
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def to_passage(row: dict) -> dict:
    """Convert a single SciFact corpus row into a flat passage dict.

    SciFact ``abstract`` field is a list of sentences; we join them into
    a single contiguous string because the abstracts are short enough
    (~150 words) that chunking is unnecessary.
    """
    abstract_text = " ".join(row["abstract"]) if row.get("abstract") else ""
    return {
        "source_id": str(row["doc_id"]),
        "title": row.get("title", ""),
        "text": abstract_text,
        "metadata": {
            "structured": row.get("structured", False),
        },
    }


def save_passages_jsonl(passages: list[dict], path: Path) -> None:
    """Persist processed passages to JSONL for fast re-ingestion."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for p in passages:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    log.info("ingest.passages_saved", path=str(path), count=len(passages))


# ---------------------------------------------------------------------------
# Main ingestion pipeline
# ---------------------------------------------------------------------------


def main(limit: int | None = None) -> None:
    """Run the full ingestion pipeline.

    Args:
        limit: If set, only ingest the first ``limit`` documents (useful
               for development and testing).
    """
    settings = get_settings()
    log.info(
        "ingest.start",
        embedding_model=settings.embedding_model,
        chroma_path=settings.chroma_path,
        limit=limit,
    )
    t0 = time.perf_counter()

    # ------------------------------------------------------------------
    # 1. Load SciFact corpus from HuggingFace
    # ------------------------------------------------------------------
    log.info("ingest.loading_dataset", dataset="allenai/scifact", config="corpus")

    # SciFact corpus is distributed as a tar.gz from S3.
    # We download it once and cache the extracted corpus.jsonl locally.
    corpus_cache = PROJECT_ROOT / "data" / "raw" / "corpus.jsonl"
    if corpus_cache.exists():
        log.info("ingest.loading_from_cache", path=str(corpus_cache))
    else:
        import io
        import ssl
        import tarfile
        import urllib.request

        # Use certifi's CA bundle so this works on macOS python.org installs
        # that don't ship system root certs. Falls back to system context.
        try:
            import certifi

            ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        except ImportError:
            ssl_ctx = ssl.create_default_context()

        archive_url = "https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz"
        log.info("ingest.downloading", url=archive_url)

        with urllib.request.urlopen(archive_url, context=ssl_ctx) as response:
            archive_bytes = response.read()

        # Extract corpus.jsonl from the archive
        corpus_cache.parent.mkdir(parents=True, exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(archive_bytes), mode="r:gz") as tar:
            # The file is at data/corpus.jsonl inside the archive
            for member in tar.getmembers():
                if member.name.endswith("corpus.jsonl"):
                    f = tar.extractfile(member)
                    if f is not None:
                        corpus_cache.write_bytes(f.read())
                        break
            else:
                raise FileNotFoundError("corpus.jsonl not found in the SciFact tar.gz archive")

        log.info("ingest.downloaded", path=str(corpus_cache))

    # Parse the JSONL file
    with open(corpus_cache, encoding="utf-8") as f:
        ds = [json.loads(line) for line in f if line.strip()]
    log.info("ingest.dataset_loaded", total_docs=len(ds))

    # ------------------------------------------------------------------
    # 2. Convert to passages
    # ------------------------------------------------------------------
    passages = [to_passage(row) for row in ds]

    # Filter out empty abstracts (shouldn't happen, but be safe)
    passages = [p for p in passages if p["text"].strip()]

    if limit:
        passages = passages[:limit]

    log.info("ingest.passages_prepared", count=len(passages))

    # Save processed passages to disk for reproducibility
    save_passages_jsonl(passages, PROCESSED_DIR / "passages.jsonl")

    # ------------------------------------------------------------------
    # 3. Embed all passages
    # ------------------------------------------------------------------
    log.info("ingest.embedding_start", n_passages=len(passages))
    embedder = Embedder()
    texts = [p["text"] for p in passages]

    # Embed in batches to manage memory
    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        batch_embeddings = embedder.embed(batch)
        all_embeddings.extend(batch_embeddings)
        log.info(
            "ingest.embedding_batch",
            batch=i // BATCH_SIZE + 1,
            total=len(texts),
            done=min(i + BATCH_SIZE, len(texts)),
        )

    log.info("ingest.embedding_done", n_embeddings=len(all_embeddings))

    # ------------------------------------------------------------------
    # 4. Upsert into ChromaDB
    # ------------------------------------------------------------------
    collection = get_collection()
    log.info("ingest.upserting", collection="scicheck", n_passages=len(passages))

    for i in range(0, len(passages), BATCH_SIZE):
        batch_passages = passages[i : i + BATCH_SIZE]
        batch_embeddings = all_embeddings[i : i + BATCH_SIZE]

        collection.upsert(
            ids=[p["source_id"] for p in batch_passages],
            documents=[p["text"] for p in batch_passages],
            metadatas=[{"title": p["title"], **p["metadata"]} for p in batch_passages],
            embeddings=batch_embeddings,
        )
        log.info(
            "ingest.upsert_batch",
            batch=i // BATCH_SIZE + 1,
            done=min(i + BATCH_SIZE, len(passages)),
        )

    elapsed = time.perf_counter() - t0

    # ------------------------------------------------------------------
    # 5. Summary
    # ------------------------------------------------------------------
    final_count = collection.count()
    log.info(
        "ingest.done",
        total_ingested=len(passages),
        collection_size=final_count,
        elapsed_seconds=round(elapsed, 2),
        embedding_dim=embedder.dim,
    )

    print(f"\n{'='*60}")
    print("  SciCheck Ingestion Complete")
    print(f"{'='*60}")
    print("  Corpus       : SciFact (allenai/scifact)")
    print(f"  Documents    : {len(passages)}")
    print(f"  Collection   : {final_count} vectors in ChromaDB")
    print(f"  Embedding    : {settings.embedding_model}")
    print(f"  Dimensions   : {embedder.dim}")
    print(f"  Chroma path  : {os.path.abspath(settings.chroma_path)}")
    print(f"  Time         : {elapsed:.1f}s")
    print(f"{'='*60}\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Ingest SciFact corpus into ChromaDB")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only ingest the first N documents (for development/testing).",
    )
    args = parser.parse_args()
    main(limit=args.limit)
