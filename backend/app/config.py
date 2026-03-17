from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    lm_studio_url: str = "http://localhost:1234/v1/chat/completions"
    model_name: str = "meta-llama-3.1-8b-instruct"
    cors_origins: str = "http://localhost:5173"
    database_url: str = ""
    chroma_path: str = ""

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
