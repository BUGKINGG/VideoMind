from dataclasses import dataclass
from pathlib import Path
import os


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


def load_local_env(env_path: str = ".env") -> None:
    path = PROJECT_ROOT / env_path
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ[key] = value


@dataclass(frozen=True)
class LLMConfig:
    auth_token: str | None
    base_url: str | None
    model: str | None


@dataclass(frozen=True)
class EmbeddingConfig:
    api_key: str | None
    base_url: str | None
    model: str | None
    dimensions: int | None = None


def get_llm_config() -> LLMConfig:
    load_local_env()
    return LLMConfig(
        auth_token=os.getenv("ANTHROPIC_AUTH_TOKEN"),
        base_url=os.getenv("ANTHROPIC_BASE_URL"),
        model=os.getenv("ANTHROPIC_MODEL"),
    )


def get_embedding_config() -> EmbeddingConfig:
    load_local_env()
    raw_dimensions = os.getenv("EMBEDDING_DIMENSIONS")
    return EmbeddingConfig(
        api_key=os.getenv("EMBEDDING_API_KEY"),
        base_url=os.getenv("EMBEDDING_BASE_URL"),
        model=os.getenv("EMBEDDING_MODEL"),
        dimensions=int(raw_dimensions) if raw_dimensions else None,
    )


def get_data_path(filename: str) -> Path:
    return DATA_DIR / filename
