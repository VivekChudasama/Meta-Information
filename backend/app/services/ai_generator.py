from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
import json
from app.core.config import settings

class SEOMetadata(BaseModel):
    seo_title: str = Field(description="The SEO-optimized title for the document.")
    seo_description: str = Field(description="The SEO-optimized description or meta summary for the document.")
    url_routes: list[str] = Field(description="A list of 3-5 suggested URL routes or slugs suitable for the document content (e.g., 'machine-learning-micromodels').")

def generate_seo_metadata(parsed_content: str) -> SEOMetadata:
    """Generates SEO metadata from extracted document content using Langchain and Groq."""
    
    # Check if GROQ_API_KEY is available
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not found in environment variables.")

    # Initialize the Groq Chat model
    llm = ChatGroq(
        model_name=settings.GROQ_MODEL,
        groq_api_key=settings.GROQ_API_KEY,
        temperature=0.7,
        max_retries=2
    )
    
    # Configure the schema output via Prompt Instructions
    prompt = PromptTemplate.from_template(
        """You are an expert SEO specialist.
        Based on the following document content extracted from a .docx file:
        
        {content}
        
        Your task is to generate SEO-optimized metadata for this document.
        Please provide:
        1. An engaging SEO Title (max 60 characters).
        2. A compelling SEO Description (max 160 characters).
        3. A list of 3 to 5 SEO-friendly URL routes (slugs).
        
        Output exclusively in valid JSON format matching this exact schema:
        {{
            "seo_title": "string",
            "seo_description": "string",
            "url_routes": ["string"]
        }}
        Do not include markdown code block syntax around the JSON.
        """
    )
    
    chain = prompt | llm
    
    # Limit content to roughly 15000 chars to avoid very large prompts
    content_to_process = parsed_content[:15000] 
    
    result = chain.invoke({"content": content_to_process})
    
    try:
        # Groq might return with markdown ```json ... ```, strip it just in case
        content = result.content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.endswith("```"):
            content = content[:-3]
        
        parsed_json = json.loads(content.strip())
        return SEOMetadata(**parsed_json)
    except Exception as e:
        print(f"Error parsing LLM output: {e}\nRaw output: {result.content}")
        # Return fallback
        return SEOMetadata(
            seo_title="Failed to generate SEO Title",
            seo_description=f"Error parsing LLM response. Raw: {result.content[:50]}...",
            url_routes=["error-generating-routes"]
        )
