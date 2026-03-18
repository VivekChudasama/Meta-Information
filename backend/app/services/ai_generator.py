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

    # Configure the schema output via Prompt Instructions
    prompt = PromptTemplate.from_template(
        """
            System: You are an expert SEO & Conversion Copywriter.
            Audience: Devs, founders, product managers and non-technical readers

            Task: Deeply analyze the provided <document> to generate SEO metadata which Improve CTR and follow the google SEO rules Strictly for the blog post.

            Provide:
            1. Primary Keyword: Identify the single most representative from the document.

            Rules:
            1. META TITLE ( Strictly UNDER 60 chars ):
            - Analyze the document's main topic and create a descriptive, keyword-rich title. End with concrete nouns: audience, or topic scope, benefit.
            - Incorporate the Primary Keyword naturally into a full phrase or headline.
            - Include specific audience or use case when relevant.
            - Be direct and descriptive—avoid vague hooks like "Unlock", "Master".
            - Focus on information delivery, not hype.

            2. META DESCRIPTION ( Strictly UNDER 150-160 chars ):
            - Identify the Problem: Open with the specific technical problem or question.
            - Briefly state the consequence of the problem and the method that fixes it.
            -  End with the strategic business benefit for the reader.
            - Action-oriented language.
            - Frame the first sentence as a "citable block"—a factual, direct answer that AI agents can extract.

            3. URL ROUTES (5 slugs):
            -  Provide 5 concise variations formatted as standard URLs.
            - Use ONLY lowercase letters and hyphens
            - Strictly NO dates, years, or numbers that will expire. Remove stop words

            CONSTRAINTS:
            - Tone: Professional, helpful, and technical. No fluff or hype.
            - No dates, years, or extra explanations
            - CRITICAL: DO NOT output any reasoning, thought process, or conversational text.
            - CRITICAL: DO NOT repeat the document content.
            
            - Output ONLY valid JSON 
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

    chain = prompt | llm

    # Limit content to roughly 15000 chars to avoid very large prompts
    content_to_process = parsed_content[:15000]

    result = chain.invoke({"content": content_to_process})

    try:
        content = result.content.strip()

        # Try to find a JSON block wrapped in ```json ... ``` or just ``` ... ```
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", content, re.DOTALL)
        if match:
            json_str = match.group(1)
        else:
            # Fallback: try to find the outermost curly braces
            match = re.search(r"(\{.*\})", content, re.DOTALL)
            if match:
                json_str = match.group(1)
            else:
                json_str = content

        parsed_json = json.loads(json_str.strip())

        return SEOMetadata(**parsed_json)
    except Exception as e:
        print(f"Error parsing LLM output: {e}\nRaw output: {result.content}")
        # Return fallback
        return SEOMetadata(
            meta_title="Failed to generate SEO Title",
            meta_description=f"Error parsing LLM response. Raw: {result.content[:50]}...",
            meta_routes=["error-generating-routes"],
        )
