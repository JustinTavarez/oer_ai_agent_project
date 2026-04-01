from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    lm_studio_url: str = "http://localhost:1234/v1/chat/completions"
    lm_studio_base_url: str = "http://localhost:1234/v1"
    model_name: str = "qwen2.5-7b-instruct"
    embedding_model: str = "text-embedding-nomic-embed-text-v1.5"
    cors_origins: str = "http://localhost:5173"
    database_url: str = ""
    chroma_path: str = "./chroma_db"
    search_log_path: str = "./logs/search_log.jsonl"

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
