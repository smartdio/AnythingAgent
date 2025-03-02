from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import Dict, List, Optional, Any
import importlib.util
import sys
from pathlib import Path
import shutil
import os
import yaml
import zipfile
import tempfile

from app.models.manager import model_manager
from app.core.logger import get_logger
from app.core.config import settings
from app.utils.common import format_error_response

logger = get_logger("models_api")
router = APIRouter()

@router.get("/models")
async def list_models() -> Dict[str, Any]:
    """
    List all available models and their configuration information.
    """
    try:
        models = model_manager.list_models()
        return {
            "data": [
                {
                    "id": name,
                    "object": "model",
                    **info
                }
                for name, info in models.items()
            ],
            "object": "list"
        }
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/models/deploy")
async def deploy_model(
    package_file: UploadFile = File(...),
    replace_existing: bool = Form(False)
) -> JSONResponse:
    """
    Deploy a new model.
    Model package should be a zip file containing:
    - main.py: Model main program
    - config.yaml: Configuration file
    - requirements.txt: Dependencies file
    - data/: Data directory (optional)
    
    Args:
        package_file: Model package file (zip format)
        replace_existing: Whether to replace existing model with the same name
    """
    try:
        # Validate file type
        if not package_file.filename.endswith('.zip'):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only zip files are allowed"
            )
        
        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Save uploaded file
            temp_zip = Path(temp_dir) / package_file.filename
            with temp_zip.open("wb") as buffer:
                shutil.copyfileobj(package_file.file, buffer)
            
            # Extract files
            with zipfile.ZipFile(temp_zip) as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Validate required files
            model_files = list(Path(temp_dir).glob("*/main.py"))
            if not model_files:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="No main.py found in model package"
                )
            
            # Get model directory
            model_dir = model_files[0].parent
            model_name = model_dir.name
            
            # Check configuration file
            config_file = model_dir / "config.yaml"
            if config_file.exists():
                try:
                    with open(config_file) as f:
                        yaml.safe_load(f)
                except Exception as e:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid config.yaml: {str(e)}"
                    )
            
            # Check target directory
            target_dir = Path("app/models") / model_name
            if target_dir.exists():
                if not replace_existing:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Model {model_name} already exists"
                    )
                shutil.rmtree(target_dir)
            
            # Copy model files to target directory
            shutil.copytree(model_dir, target_dir)
            
            try:
                # Reload all models
                model_manager.reload_models()
                
                return JSONResponse(
                    status_code=status.HTTP_200_OK,
                    content={
                        "message": "Model deployed successfully",
                        "model": model_name
                    }
                )
            except Exception as e:
                # If loading fails, delete copied files
                shutil.rmtree(target_dir)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to load model: {str(e)}"
                )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deploying model: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete("/models/{model_name}")
async def delete_model(model_name: str) -> JSONResponse:
    """
    Delete specified model.
    
    Args:
        model_name: Model name
    """
    try:
        model_dir = Path("app/models") / model_name
        if not model_dir.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model {model_name} not found"
            )
        
        # Delete model directory
        shutil.rmtree(model_dir)
        
        # Reload all models
        model_manager.reload_models()
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": "Model deleted successfully",
                "model": model_name
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting model: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post("/models/reload")
async def reload_models() -> JSONResponse:
    """
    Reload all models.
    """
    try:
        model_manager.reload_models()
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "All models reloaded successfully"}
        )
    except Exception as e:
        logger.error(f"Error reloading models: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        ) 