"""
WBS BPKH AI - File Upload Router
=================================
Secure file upload endpoints for report attachments.
"""

import uuid
import os
from typing import List
from fastapi import APIRouter, HTTPException, UploadFile, File
from loguru import logger

from config import GENERIC_ERROR_MESSAGE
from database import SupabaseDB

router = APIRouter(prefix="/api/v1/uploads", tags=["Uploads"])

# Allowed file types and size limits
ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".xls", ".xlsx",
    ".jpg", ".jpeg", ".png", ".gif", ".webp",
    ".mp3", ".mp4", ".wav",
    ".txt", ".csv", ".zip",
}
ALLOWED_MIME_PREFIXES = {
    "image/", "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument",
    "application/vnd.ms-excel",
    "audio/", "video/mp4",
    "text/plain", "text/csv",
    "application/zip",
}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB per file
MAX_FILES_PER_UPLOAD = 5
STORAGE_BUCKET = "attachments"


def _validate_file(file: UploadFile) -> None:
    """Validate file extension and content type."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nama file tidak boleh kosong")

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Tipe file '{ext}' tidak diizinkan. "
                   f"Format yang diterima: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content_type = file.content_type or ""
    if not any(content_type.startswith(prefix) for prefix in ALLOWED_MIME_PREFIXES):
        raise HTTPException(
            status_code=400,
            detail=f"Content type '{content_type}' tidak diizinkan",
        )


@router.post("")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Upload one or more files (max 5, max 10MB each).
    Returns list of file IDs for attaching to reports.
    Public endpoint (no auth required — reporters are anonymous).
    """
    if len(files) > MAX_FILES_PER_UPLOAD:
        raise HTTPException(
            status_code=400,
            detail=f"Maksimal {MAX_FILES_PER_UPLOAD} file per upload",
        )

    uploaded = []

    for file in files:
        _validate_file(file)

        # Read and check size
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File '{file.filename}' terlalu besar. Maksimal 10MB per file.",
            )

        ext = os.path.splitext(file.filename)[1].lower()
        file_id = uuid.uuid4().hex[:16]
        storage_path = f"{file_id}{ext}"

        try:
            db = SupabaseDB.get_client()
            db.storage.from_(STORAGE_BUCKET).upload(
                path=storage_path,
                file=content,
                file_options={
                    "content-type": file.content_type or "application/octet-stream",
                },
            )
            uploaded.append({
                "file_id": file_id,
                "filename": file.filename,
                "size": len(content),
                "content_type": file.content_type,
                "storage_path": storage_path,
            })
            logger.info(f"File uploaded: {file.filename} -> {storage_path}")

        except Exception as e:
            logger.error(f"Failed to upload file {file.filename}: {e}")
            # If Supabase storage not configured, fall back to returning file metadata
            # so the system is still usable without storage
            uploaded.append({
                "file_id": file_id,
                "filename": file.filename,
                "size": len(content),
                "content_type": file.content_type,
                "storage_path": storage_path,
                "storage_error": str(e),
            })

    return {
        "message": f"{len(uploaded)} file berhasil diupload",
        "files": uploaded,
    }
