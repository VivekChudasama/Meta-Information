import os
import shutil
import tempfile
from fastapi import UploadFile, HTTPException
from fastapi.concurrency import run_in_threadpool
from app.services.parser import parse_docx_to_markdown
from app.services.ai_generator import generate_seo_metadata, SEOMetadata

async def process_metadata_generation(file: UploadFile) -> SEOMetadata:
    """
    Controller logic to handle the flow:
    1. Upload file to temp
    2. Parse content
    3. Generate SEO metadata via LLM
    """
    if not file.filename or not file.filename.endswith(".docx"):
        raise HTTPException(status_code=400, detail="Only .docx files are permitted.")

    try:
        # Create a temporary file to save the uploaded docx
        fd, temp_path = tempfile.mkstemp(suffix=".docx")
        with os.fdopen(fd, "wb") as f_out:
            shutil.copyfileobj(file.file, f_out)

        # 1. Parse the document using a background thread to prevent blocking event loop
        parsed_markdown = await run_in_threadpool(parse_docx_to_markdown, temp_path)

        # 2. Delete the temporary file promptly
        os.remove(temp_path)

        # 3. Call the AI model
        print(f"[Controller] Generating SEO metadata for: {file.filename}")
        metadata = await generate_seo_metadata(parsed_markdown)

        return metadata

    except Exception as e:
        print(f"Error in controller during processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))
