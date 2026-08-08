"""Environment-driven configuration.

All runtime configuration funnels through ``Settings``. Adapters and pipeline
stages receive what they need via dependency injection rather than reading the
environment directly — this keeps tests deterministic and adapters swappable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Top-level application settings.

    Values are loaded from environment variables prefixed with ``DISTILL_`` and
    from a local ``.env`` file when present. Provider-specific secrets (e.g.
    ``ANTHROPIC_API_KEY``, ``NEO4J_PASSWORD``) are read without the prefix to
    match the conventional names of those SDKs.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="DISTILL_",
        extra="ignore",
    )

    # Pipeline behavior
    tenant_id: str = "default"
    log_level: str = "INFO"

    # Chunking
    chunk_token_size: int = 800
    chunk_token_overlap: int = 100

    # LLM
    llm_provider: Literal["fake", "anthropic", "omlx"] = "fake"
    llm_model: str = "claude-sonnet-4-5"
    llm_max_concurrency: int = 4

    # OMLX
    omlx_base_url: str = "http://localhost:8000/v1"

    # Embeddings
    embedder_provider: Literal["fake", "anthropic", "omlx"] = "fake"
    embedder_model: str = "Qwen3.6-35B-A3B-4bit"

    # Graph
    graph_backend: Literal["in_memory", "neo4j"] = "in_memory"
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = Field(default="neo4j", validation_alias="NEO4J_USER")
    neo4j_password: str = Field(default="", validation_alias="NEO4J_PASSWORD")

    # Dead letter
    dead_letter_dir: Path = Path("./dead_letter")

    # Secrets read without the DISTILL_ prefix
    anthropic_api_key: str = Field(default="", validation_alias="ANTHROPIC_API_KEY")
    omlx_api_key: str = Field(default="", validation_alias="OMLX_API_KEY")


def get_settings() -> Settings:
    """Build a fresh ``Settings`` instance.

    Kept as a function (not a module-level singleton) so tests can monkeypatch
    environment variables and call this for isolated configs.
    """
    return Settings()
