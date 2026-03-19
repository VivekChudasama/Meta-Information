from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field
import json
import re

from app.core.config import settings


class SEOMetadata(BaseModel):
    meta_title: str = Field(description="The SEO-optimized title for the document.")
    meta_description: str = Field(
        description="The SEO-optimized description or meta summary for the document."
    )
    meta_routes: list[str] = Field(
        description="A list of 3-5 suggested URL routes or slugs suitable for the document content (e.g., 'machine-learning-micromodels')."
    )


def generate_seo_metadata(parsed_content: str) -> SEOMetadata:
    """Generates SEO metadata from extracted document content using Langchain and Groq."""

    # Check if GROQ_API_KEY is available
    if not settings.GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not found in environment variables.")

    # Initialize the Groq Chat model
    # Groq automatically caches the static system prompt prefix server-side.
    # Only the dynamic document content changes per request — it is never stored.
    llm = ChatGroq(
        model_name=settings.GROQ_MODEL,
        groq_api_key=settings.GROQ_API_KEY,
        temperature=0.4,
        max_retries=3,
        model_kwargs={"top_p": 0.9},
    )

    # By using structured output with method="json_mode" we force the model to
    # output strict JSON instead of spending tokens reasoning or chatting.
    structured_llm = llm.with_structured_output(SEOMetadata, method="json_mode")

    # Configure the schema output via Prompt Instructions
    prompt = PromptTemplate.from_template(
        """
        System: You are a senior SEO strategist and conversion copywriter.

        Audience: Devs, founders, product managers, and non-technical readers.

        Task: Analyze the <document> and output structured SEO metadata that improves CTR and follows Google SEO best practices.

        Provide:
            1. Primary Keyword: The most relevant search phrase that best rep core topic"
        
        Language rules:
        - Include articles and prepositions where grammar requires them

        RULES:
        1. META TITLE (40-60 chars, hard limits):
        - Analyze the document's main topic and create a descriptive, keyword-rich title
        PART 1 → What the page is about
        PART 2 → What the reader gets — action-phrased and value-driven.
        - Include the primary keyword naturally

       
        2. META DESCRIPTION (140-160 chars, hard limits):
            PART 1 → Sharp conversational question mirroring reader's search
            PART 2 → Name 2-3 specific things from the document only — no filler
            - Naturally weave in the primary keyword without forcing it
            - Match the search intent of the document and Tone : Conversational, speaks directly to reader ,no invented claims
            - Natural verbs only

        3. URL ROUTES (5 slugs):
           - Derived from Key topics in the document
           - Lowercase and hyphens only — no dates, years, numbers.
           - Each slug must be a descriptive phrase, not a shortened fragment

        CONSTRAINTS:
        - No dates, years, or commentary in output
        - Tone matches document (technical / casual / formal)
        - Every claim from document only — never invent
        - Read every field aloud before finalizing — if it sounds clipped or robotic, rewrite it
        - Output ONLY valid JSON

        OUTPUT SCHEMA:
        {{
            "meta_title": "string",
            "meta_description": "string",
            "meta_routes": ["string", "string", "string", "string", "string"]
        }}

        <document>
        {content}
        </document>
        """
    )

    chain = prompt | structured_llm

    # Limit content to roughly 15000 chars to avoid very large prompts
    content_to_process = parsed_content[:15000]

    print(f"[AI Generator] Using model: {settings.GROQ_MODEL}")

    try:
        result = chain.invoke({"content": content_to_process})
    except Exception as api_err:
        print(
            f"[AI Generator] API call FAILED — model '{settings.GROQ_MODEL}' may be invalid or unsupported."
        )
        print(f"[AI Generator] API error: {api_err}")
        return SEOMetadata(
            meta_title="Failed to generate SEO Title",
            meta_description="API call failed. Check that the model name in config.py is a valid Groq model.",
            meta_routes=["error-generating-routes"],
        )

    # We skip regex extraction, because structured output guarantees parsing
    try:
        return result
    except Exception as e:
        print(f"[AI Generator] Error parsing LLM output: {e}")
        # Return fallback
        return SEOMetadata(
            meta_title="Failed to generate SEO Title",
            meta_description=f"Error parsing LLM response.",
            meta_routes=["error-generating-routes"],
        )
