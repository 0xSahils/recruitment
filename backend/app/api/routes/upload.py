import uuid
import asyncio
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from app.schemas import UploadResponse, BatchStatusResponse, UploadFileStatus
from app.api.deps import get_current_user
from app.db import async_session
from app.parsing.pipeline import process_single_pdf
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory batch tracking (sufficient for beta with 1 recruiter)
_batches: dict[str, dict] = {}


async def _process_batch(batch_id: str, files_data: list[tuple[str, bytes]]):
    batch = _batches[batch_id]
    for filename, pdf_bytes in files_data:
        try:
            async with async_session() as session:
                result = await process_single_pdf(session, pdf_bytes, filename)
                await session.commit()

                file_status = UploadFileStatus(
                    filename=filename,
                    status="parsed" if result["status"] == "success" else "failed",
                    reason=result.get("reason"),
                    candidate_id=result.get("candidate_id"),
                    is_update=result.get("is_update", False),
                )
                batch["files"].append(file_status)
                batch["processed"] += 1
                if result["status"] == "success":
                    batch["succeeded"] += 1
                else:
                    batch["failed"] += 1

        except Exception as e:
            logger.error(f"Error processing {filename}: {e}")
            batch["files"].append(UploadFileStatus(
                filename=filename,
                status="failed",
                reason=str(e),
            ))
            batch["processed"] += 1
            batch["failed"] += 1

    batch["status"] = "completed" if batch["failed"] == 0 else "completed_with_errors"


@router.post("/candidates/upload", response_model=UploadResponse, status_code=202)
async def upload_pdfs(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    user: str = Depends(get_current_user),
):
    pdf_files = [f for f in files if f.filename and f.filename.lower().endswith(".pdf")]
    if not pdf_files:
        raise HTTPException(status_code=400, detail="No PDF files provided")

    batch_id = str(uuid.uuid4())
    files_data = []
    for f in pdf_files:
        content = await f.read()
        files_data.append((f.filename, content))

    _batches[batch_id] = {
        "total": len(files_data),
        "processed": 0,
        "succeeded": 0,
        "failed": 0,
        "status": "processing",
        "files": [],
    }

    background_tasks.add_task(_process_batch, batch_id, files_data)

    return UploadResponse(
        batch_id=batch_id,
        files_received=len(files_data),
        status="processing",
    )


@router.get("/candidates/upload/{batch_id}/status", response_model=BatchStatusResponse)
async def get_upload_status(batch_id: str, user: str = Depends(get_current_user)):
    batch = _batches.get(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    return BatchStatusResponse(
        batch_id=batch_id,
        total=batch["total"],
        processed=batch["processed"],
        succeeded=batch["succeeded"],
        failed=batch["failed"],
        status=batch["status"],
        files=batch["files"],
    )
