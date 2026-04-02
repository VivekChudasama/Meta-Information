from fastapi import APIRouter, File, UploadFile, Form
from app.controllers.generate import process_metadata_generation
from app.services.ai_generator import SEOMetadata

router = APIRouter(tags=["generation"])

@router.post("/generate-metadata", response_model=SEOMetadata)
async def generate_metadata(
    primary_keyword: str = Form("", description="The main keyword for SEO."),
    file: UploadFile = File(..., description="The .docx file to parse.")
):
    """
    Generate SEO metadata from an uploaded .docx file.
    """
    return await process_metadata_generation(file, primary_keyword)
