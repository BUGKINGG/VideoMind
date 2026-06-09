from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import urllib.error
import urllib.request

from app.core.config import EmbeddingConfig, get_embedding_config


class EmbeddingClient:
    def embed(self, text: str) -> list[float]:
        raise NotImplementedError

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        return [self.embed(text) for text in texts]


@dataclass
class HashEmbeddingClient(EmbeddingClient):
    dimension: int = 256

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        tokens = self._tokenize(text)

        for token in tokens:
            index = self._hash_to_index(token)
            vector[index] += 1.0

        return self._normalize(vector)

    def _tokenize(self, text: str) -> list[str]:
        cleaned = "".join(char.lower() for char in text if not char.isspace())
        if not cleaned:
            return []

        tokens = list(cleaned)
        tokens.extend(cleaned[index : index + 2] for index in range(max(len(cleaned) - 1, 0)))
        return tokens

    def _hash_to_index(self, token: str) -> int:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        return int.from_bytes(digest[:4], "big") % self.dimension

    def _normalize(self, vector: list[float]) -> list[float]:
        length = math.sqrt(sum(value * value for value in vector))
        if length == 0:
            return vector
        return [value / length for value in vector]


@dataclass
class OpenAICompatibleEmbeddingClient(EmbeddingClient):
    config: EmbeddingConfig

    @classmethod
    def from_env(cls) -> "OpenAICompatibleEmbeddingClient":
        return cls(config=get_embedding_config())

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not self.config.api_key or not self.config.base_url or not self.config.model:
            raise RuntimeError(
                "Embedding API is not configured. Set EMBEDDING_API_KEY, "
                "EMBEDDING_BASE_URL and EMBEDDING_MODEL in .env."
            )

        url = self.config.base_url.rstrip("/") + "/v1/embeddings"
        payload = {
            "model": self.config.model,
            "input": texts,
        }
        request = urllib.request.Request(
            url=url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config.api_key}",
            },
        )

        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Embedding API returned HTTP {error.code}: {detail}") from error
        except urllib.error.URLError as error:
            raise RuntimeError("Cannot connect to the embedding API.") from error

        items = sorted(data.get("data", []), key=lambda item: item.get("index", 0))
        vectors = [item["embedding"] for item in items if "embedding" in item]
        if len(vectors) != len(texts):
            raise RuntimeError("Embedding API returned an unexpected number of vectors.")
        return vectors


@dataclass
class FallbackEmbeddingClient(EmbeddingClient):
    primary: EmbeddingClient
    fallback: EmbeddingClient

    def embed(self, text: str) -> list[float]:
        return self.embed_many([text])[0]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        try:
            return self.primary.embed_many(texts)
        except RuntimeError:
            return self.fallback.embed_many(texts)


def get_default_embedding_client() -> EmbeddingClient:
    config = get_embedding_config()
    if config.api_key and config.base_url and config.model:
        return FallbackEmbeddingClient(
            primary=OpenAICompatibleEmbeddingClient(config=config),
            fallback=HashEmbeddingClient(),
        )
    return HashEmbeddingClient()
