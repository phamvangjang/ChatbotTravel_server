from pydantic_settings import BaseSettings
from functools import lru_cache
import os
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # API Keys
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    MAPBOX_ACCESS_TOKEN: str = os.getenv("MAPBOX_ACCESS_TOKEN", "")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./travel_assistant.db")
    
    # App Settings
    SUPPORTED_LANGUAGES: list = ["en", "vi", "fr", "es", "zh"]
    MAX_AUDIO_SIZE_MB: int = 10
    DEFAULT_RECOMMENDATIONS_COUNT: int = 5

    class Config:
        env_file = ".env"

@lru_cache()
def get_settings():
    return Settings() 