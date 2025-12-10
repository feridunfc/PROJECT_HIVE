from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional

class Settings(BaseSettings):
    APP_NAME: str = "PROJECT_HIVE"
    ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    OPENAI_API_KEY: Optional[str] = None
    OLLAMA_BASE_URL: str = "http://localhost:11434/v1"
    DEFAULT_CLOUD_MODEL: str = "gpt-4o"
    DEFAULT_LOCAL_MODEL: str = "llama3"
    MAX_TOKENS: int = 4000
    MAX_RETRIES: int = 3
    TIMEOUT: int = 60
    MAX_SWARM_ROUNDS: int = 5
    CONSENSUS_THRESHOLD: float = 0.8
    ENABLE_SELF_HEALING: bool = True
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
