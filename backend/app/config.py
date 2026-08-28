from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    fortyguard_api_key: str = ""
    fortyguard_base_url: str = "https://api.fortyguard.com"

    gemini_api_key: str = ""
    gemini_model: str = "gemini-flash-lite-latest"

    demo_mode: bool = True
    cache_db_path: str = "./data/app.db"
    cors_origins: str = "http://localhost:5173"

    nominatim_base_url: str = "https://nominatim.openstreetmap.org"

    max_agent_turns: int = 12
    agent_timeout_s: int = 180
    poll_backoff_s: str = "3,6,12,12,12"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def poll_backoff_list(self) -> list[float]:
        return [float(x) for x in self.poll_backoff_s.split(",") if x.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
