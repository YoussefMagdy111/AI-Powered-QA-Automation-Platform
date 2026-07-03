from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    groq_api_key: str = ""
    groq_base_url: str = "https://api.groq.com/openai/v1"
    groq_model_main: str = "llama-3.3-70b-versatile"
    groq_model_reviewer: str = "llama-3.1-8b-instant"

    app_host: str = "0.0.0.0"
    app_port: int = 5000


settings = Settings()
