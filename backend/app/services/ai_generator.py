from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
import json
import re
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
            System: You are an expert SEO & Conversion Copywriter.
            Audience: Devs, founders, product managers, or non-technical readers

            Task: Analyze the provided document and generate highly clickable SEO metadata and URL slugs.

            Rules:
            1. META TITLE ( 50-60 chars):
            - Format: [Primary Keyword] + [Hook/Value]: [Benefit]
            - Must sound natural, punchy, and click-worthy.

            2. META DESCRIPTION ( 150-160 chars):
            - Format: [Pain/Question Hook ?] [Audience] get [Specific Solution/Promise] to [CTA/Benefit].
            - Hook the reader with a pain point or question first.
            - Action-oriented language.

            3. URL ROUTES (3-5 slugs):
            - Extract from core H2/H3 topics. Strictly lowercase-hyphenated.

            Output Constraints:
            - Output ONLY valid JSON and no explanations.
            Schema:
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
        # Strip any markdown code fences (```json ... ```, ``` ... ```, etc.)
        content = result.content.strip()
        content = re.sub(r'^```\w*\s*', '', content)
        content = re.sub(r'\s*```$', '', content)

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
