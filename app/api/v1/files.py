import os
import aiofiles
import json
from fastapi import APIRouter, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse as FastAPIFileResponse
from typing import List, Dict
from pathlib import Path

from app.schemas.file import FileResponse, FileListResponse, FileDeleteResponse
from app.utils.common import generate_id, get_current_timestamp
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("files")
router = APIRouter()

# Allowed file types
ALLOWED_FILE_TYPES = {
    # Text and data files
    "txt": "text/plain",
    "json": "application/json",
    "csv": "text/csv",
    
    # Microsoft Office documents
    "doc": "application/msword",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ppt": "application/vnd.ms-powerpoint",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    
    # PDF documents
    "pdf": "application/pdf",
    
    # Image files
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
    "bmp": "image/bmp",
    "webp": "image/webp",
    "svg": "image/svg+xml",
    
    # Other common formats
    "md": "text/markdown",
    "yaml": "application/x-yaml",
    "yml": "application/x-yaml"
}

def get_file_metadata(file_path: str, original_filename: str, purpose: str) -> dict:
    """Get file metadata"""
    path = Path(file_path)
    file_ext = path.suffix[1:].lower()
    return {
        "filename": original_filename,
        "purpose": purpose,
        "size": path.stat().st_size,
        "file_type": file_ext,
        "content_type": ALLOWED_FILE_TYPES.get(file_ext, "application/octet-stream"),
        "created": int(path.stat().st_ctime),
        "path": str(path.relative_to(settings.UPLOAD_DIR))
    }

@router.post("/files", response_model=FileResponse)
async def upload_file(
    file: UploadFile = File(...),
    purpose: str = "fine-tune",
) -> FileResponse:
    """
    Upload file.

    Args:
        file: File to upload.
        purpose: File purpose.

    Returns:
        File information.
    """
    try:
        # Check file size
        file_size = 0
        chunk_size = 1024 * 1024  # 1MB
        while chunk := await file.read(chunk_size):
            file_size += len(chunk)
            if file_size > settings.MAX_FILE_SIZE:
                logger.warning(f"File too large: {file.filename}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File too large. Maximum size allowed is {settings.MAX_FILE_SIZE/(1024*1024)}MB"
                )
        await file.seek(0)

        # Check file type
        file_ext = file.filename.split(".")[-1].lower()
        if file_ext not in ALLOWED_FILE_TYPES:
            logger.warning(f"File type not allowed: {file_ext}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File type '{file_ext}' not allowed. Allowed types are: {', '.join(ALLOWED_FILE_TYPES.keys())}"
            )

        # Check Content-Type (if provided)
        if file.content_type and file.content_type != ALLOWED_FILE_TYPES[file_ext]:
            logger.warning(f"Content-Type mismatch: {file.content_type} vs {ALLOWED_FILE_TYPES[file_ext]}")

        # Ensure upload directory exists
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

        # Generate file ID and save path
        file_id = generate_id("file-")
        file_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}.{file_ext}")

        # Save file
        async with aiofiles.open(file_path, "wb") as f:
            await f.write(await file.read())

        # Get file metadata
        metadata = get_file_metadata(file_path, file.filename, purpose)
        
        # Save metadata
        metadata_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}.meta.json")
        async with aiofiles.open(metadata_path, "w") as f:
            await f.write(json.dumps(metadata))

        logger.info(f"File uploaded successfully: {file.filename}")
        return FileResponse(
            id=file_id,
            **metadata
        )

    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/files", response_model=FileListResponse)
async def list_files() -> FileListResponse:
    """
    List all files.

    Returns:
        List of files.
    """
    try:
        files = []
        if os.path.exists(settings.UPLOAD_DIR):
            for filename in os.listdir(settings.UPLOAD_DIR):
                if filename.startswith("file-") and not filename.endswith(".meta.json"):
                    file_id = filename.split(".")[0]
                    metadata_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}.meta.json")
                    
                    try:
                        async with aiofiles.open(metadata_path, "r") as f:
                            metadata = json.loads(await f.read())
                            files.append(FileResponse(
                                id=file_id,
                                **metadata
                            ))
                    except Exception as e:
                        logger.error(f"Error reading metadata for {file_id}: {str(e)}")
                        # If metadata file doesn't exist or is corrupted, use basic information
                        file_path = os.path.join(settings.UPLOAD_DIR, filename)
                        metadata = get_file_metadata(file_path, filename, "unknown")
                        files.append(FileResponse(
                            id=file_id,
                            **metadata
                        ))

        logger.info(f"Listed {len(files)} files")
        return FileListResponse(data=files)

    except Exception as e:
        logger.error(f"Error listing files: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/files/{file_id}/download")
async def download_file(file_id: str):
    """
    Download file.

    Args:
        file_id: File ID.

    Returns:
        File content.
    """
    try:
        # Find file
        if os.path.exists(settings.UPLOAD_DIR):
            for filename in os.listdir(settings.UPLOAD_DIR):
                if filename.startswith(file_id) and not filename.endswith(".meta.json"):
                    file_path = os.path.join(settings.UPLOAD_DIR, filename)
                    
                    # Read metadata
                    metadata_path = os.path.join(settings.UPLOAD_DIR, f"{file_id}.meta.json")
                    try:
                        async with aiofiles.open(metadata_path, "r") as f:
                            metadata = json.loads(await f.read())
                    except Exception:
                        metadata = get_file_metadata(file_path, filename, "unknown")
                    
                    return FastAPIFileResponse(
                        file_path,
                        media_type=metadata["content_type"],
                        filename=metadata["filename"]
                    )
        
        logger.warning(f"File not found: {file_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File {file_id} not found"
        )

    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/files/{file_id}", response_model=FileDeleteResponse)
async def delete_file(
    file_id: str,
) -> FileDeleteResponse:
    """
    Delete file.

    Args:
        file_id: File ID.

    Returns:
        Delete result.
    """
    try:
        deleted = False
        if os.path.exists(settings.UPLOAD_DIR):
            # Delete file and metadata
            for filename in os.listdir(settings.UPLOAD_DIR):
                if filename.startswith(file_id):
                    file_path = os.path.join(settings.UPLOAD_DIR, filename)
                    os.remove(file_path)
                    deleted = True
                    logger.info(f"Deleted {filename}")

        if not deleted:
            logger.warning(f"File not found: {file_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"File {file_id} not found"
            )

        return FileDeleteResponse(
            id=file_id,
            deleted=True
        )

    except Exception as e:
        logger.error(f"Error deleting file: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 