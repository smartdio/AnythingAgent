from typing import List, Optional
from pydantic import BaseModel, Field

class FileResponse(BaseModel):
    """File response model"""
    id: str = Field(..., description="File ID")
    object: str = Field("file", description="Object type")
    filename: str = Field(..., description="File name")
    purpose: str = Field(..., description="File purpose")
    created: int = Field(..., description="Creation timestamp")
    size: int = Field(..., description="File size (bytes)")
    file_type: str = Field(..., description="File type")
    content_type: str = Field(..., description="File MIME type")
    path: str = Field(..., description="File relative path")

class FileListResponse(BaseModel):
    """File list response model"""
    data: List[FileResponse] = Field(..., description="List of files")
    object: str = Field("list", description="Object type")

class FileDeleteResponse(BaseModel):
    """File delete response model"""
    id: str = Field(..., description="Deleted file ID")
    object: str = Field("file", description="Object type")
    deleted: bool = Field(..., description="Whether deletion was successful")

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    code: int = Field(..., description="Error code") 