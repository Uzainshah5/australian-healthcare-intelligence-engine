import os
from pathlib import Path
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    # Base crawler configuration
    base_url: str = "https://www.hotdoc.com.au"
    target_sample_size: int = 60
    max_sample_size: int = 75
    
    # Polite rate limiting & timeouts
    min_delay_seconds: float = 2.5
    max_delay_seconds: float = 4.5
    page_timeout_ms: int = 30000
    max_retries: int = 2
    headless: bool = True
    
    # User agent mimicking modern desktop browser
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    viewport_width: int = 1440
    viewport_height: int = 900
    
    # Paths
    project_root: Path = PROJECT_ROOT
    db_path: Path = PROJECT_ROOT / "data" / "checkpoints.db"
    exports_dir: Path = PROJECT_ROOT / "data" / "exports"
    config_dir: Path = PROJECT_ROOT / "config"
    
    # AI API keys & endpoints (OpenAI, OpenRouter, Groq, Gemini)
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = "gpt-4o-mini"
    gemini_api_key: str = ""
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

# Ensure runtime directories exist
settings.db_path.parent.mkdir(parents=True, exist_ok=True)
settings.exports_dir.mkdir(parents=True, exist_ok=True)
