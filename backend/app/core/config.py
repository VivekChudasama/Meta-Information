import os
from pydantic_settings import BaseSettings  
from dotenv import load_dotenv 

# Load from specific environment folder
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '../../environment/.env'))

class Settings(BaseSettings):
    PROJECT_NAME: str = "SEO Metadata Generator API"
    API_V1_STR: str = "/api/v1"
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = "openai/gpt-oss-120b"

settings = Settings()
