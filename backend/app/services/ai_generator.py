from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
import json
from app.core.config import settings


class SEOMetadata(BaseModel):
    seo_title: str = Field(description="The SEO-optimized title for the document.")
    seo_description: str = Field(
        description="The SEO-optimized description or meta summary for the document."
    )
    url_routes: list[str] = Field(
        description="A list of 3-5 suggested URL routes or slugs suitable for the document content (e.g., 'machine-learning-micromodels')."
    )


def generate_seo_metadata(parsed_content: str) -> SEOMetadata:
    """Generates SEO metadata from extracted document content using Langchain and Groq."""

    # Check if GROQ_API_KEY is available
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not found in environment variables.")

    # Initialize the Groq Chat model
    llm = ChatGroq(
        model_name=settings.GROQ_MODEL,
        groq_api_key=settings.GROQ_API_KEY,
        temperature=0.5,
        max_retries=3,
        model_kwargs={"top_p": 0.9},
    )

    # Configure the schema output via Prompt Instructions
    prompt = PromptTemplate.from_template(
        """ 
            System: Technical SEO Specialist
            Task: Generate strictly valid JSON metadata for the <document>. 
            Audience: Devs & Tech Leads
            Tone: Clear, benefit-focused

            Rules:
            - Output ONLY raw JSON.
            - Title: 50-60 chars. [Primary Keyword] + Guide/Explained (Only add the Current Year if it is strictly necessary/relevant to the content).
            - Description: 150-160 chars. Flow: [Problem solved] -> [Target audience] -> [Key outcome].
            - Routes: 3-5 slugs from H2/H3. Lowercase-hyphenated, keyword variants.

            JSON Schema:
            {{
            "seo_title": "string",
            "seo_description": "string",
            "url_routes": ["string"]
            }}
            <document>
            {content}
            </document>
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
            url_routes=["error-generating-routes"],
        )
