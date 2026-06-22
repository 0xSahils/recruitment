"""
Bulk PDF seeder — processes all PDFs in a folder directly (no HTTP overhead).
Usage:  python seed_candidates.py <folder_path>
Example: python seed_candidates.py ./sample_pdfs

Processes sequentially (Ollama is single-threaded on CPU).
Shows progress and timing per file. Safe to Ctrl+C and resume —
already-imported candidates are detected by identity resolution.
"""
import sys
import asyncio
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.db import async_session
from app.parsing.pipeline import process_single_pdf
from app.vector_db import init_qdrant_collection
from app.embeddings.generator import load_models
from app.llm.client import warmup


async def seed(folder: Path):
    pdf_files = sorted(folder.glob("*.pdf"))
    if not pdf_files:
        print(f"No PDF files found in {folder}")
        return

    print(f"Found {len(pdf_files)} PDFs in {folder}")
    print("Initializing models...")

    await init_qdrant_collection()
    load_models()
    await warmup()

    print(f"\nProcessing {len(pdf_files)} PDFs...\n")

    succeeded = 0
    failed = 0
    total_time = 0

    for i, pdf_path in enumerate(pdf_files, 1):
        start = time.time()
        pdf_bytes = pdf_path.read_bytes()

        try:
            async with async_session() as session:
                result = await process_single_pdf(session, pdf_bytes, pdf_path.name)
                await session.commit()

            elapsed = time.time() - start
            total_time += elapsed

            if result["status"] == "success":
                succeeded += 1
                label = "UPDATED" if result["is_update"] else "NEW"
                print(f"  [{i}/{len(pdf_files)}] {label}  {pdf_path.name}  ({elapsed:.1f}s)")
            else:
                failed += 1
                print(f"  [{i}/{len(pdf_files)}] FAIL  {pdf_path.name}  — {result['reason']}  ({elapsed:.1f}s)")

        except Exception as e:
            elapsed = time.time() - start
            total_time += elapsed
            failed += 1
            print(f"  [{i}/{len(pdf_files)}] ERROR {pdf_path.name}  — {e}  ({elapsed:.1f}s)")

        avg = total_time / i
        remaining = avg * (len(pdf_files) - i)
        print(f"           avg {avg:.1f}s/pdf  |  ~{remaining/60:.0f}min remaining")

    print(f"\nDone: {succeeded} succeeded, {failed} failed, {total_time/60:.1f} min total")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python seed_candidates.py <folder_with_pdfs>")
        sys.exit(1)

    folder = Path(sys.argv[1])
    if not folder.is_dir():
        print(f"Not a directory: {folder}")
        sys.exit(1)

    asyncio.run(seed(folder))
