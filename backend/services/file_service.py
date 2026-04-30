"""
services/file_service.py
────────────────────────
Handles saving PDFs to disk and cleaning them up on delete.
Each user gets their own sub-folder: data/uploads/<user_id>/
"""

import uuid
import shutil
from pathlib import Path
from fastapi import UploadFile, HTTPException

from backend.core.config import settings

def get_user_upload_dir(user_id: int) -> Path:
    """Returns the Path object for the user's upload directory, creating it if necessary."""
    user_dir = Path(settings.UPLOAD_DIR) / str(user_id)
    user_dir.mkdir(parents=True, exist_ok=True)
    return user_dir

def save_pdf(user_id: int, upload_file: UploadFile) -> dict:

    """Saves the uploaded file to the user's directory with a unique name. Returns the file path."""

    if not upload_file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed.")
    
    # Use a UUID to avoid name collisions on disk while keeping the original name in DB
    user_dir = get_user_upload_dir(user_id)

    # Use a UUID to avoid name collisions on disk while keeping the original name in DB
    stored_name = f"{uuid.uuid4().hex}.pdf"
    file_path = user_dir / stored_name

    # write the file to disk
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)

    file_size_kb = file_path.stat().st_size // 1024

    return {
        "stored_name": stored_name,
        "file_path": str(file_path),
        "file_size_kb": file_size_kb
    }

def delete_pdf(file_path: str):
    """Delete the PDF file from disk. Silently ignores missing files."""
    path = Path(file_path)
    if path.exists():
        path.unlink()
