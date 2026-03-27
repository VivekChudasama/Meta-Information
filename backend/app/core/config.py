import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load from specific environment folder
load_dotenv(os.path.join(os.getcwd(), "environment", ".env"))


class Settings(BaseSettings):
    PROJECT_NAME: str = "SEO Metadata Generator API"
    API_V1_STR: str = "/api/v1"
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = "meta-llama/llama-4-scout-17b-16e-instruct"
 
settings = Settings()
  