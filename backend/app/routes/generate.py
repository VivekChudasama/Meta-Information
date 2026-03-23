from fastapi import APIRouter, File, UploadFile
from app.controllers.generate import process_metadata_generation
from app.services.ai_generator import SEOMetadata

router = APIRouter(tags=["generation"])


@router.post("/generate-metadata", response_model=SEOMetadata)
async def generate_metadata(file: UploadFile = File(...)):
    """
    Receives an uploaded .docx file and orchestrates parsing + metadata generation via the controller.
    """
    return await process_metadata_generation(file)
