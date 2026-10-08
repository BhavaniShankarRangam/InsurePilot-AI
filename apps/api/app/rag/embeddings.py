"""Embedding providers. `HashingEmbedder` works offline; OpenAI is used when configured."""

import hashlib
import math
from functools import lru_cache
from typing import Protocol

import httpx

from app.core.config import get_settings
from app.rag.text import tokenize


class Embedder(Protocol):
    name: str
    dim: int

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashingEmbedder:
    """Deterministic feature-hashing embedder over unigrams + bigrams.

    Lexical rather than semantic, but stable, fast and dependency-free — suitable
    for demo mode and tests. Swap for a neural embedder in production.
    """

    name = "local-hashing-v1"

    def __init__(self, dim: int) -> None:
        self.dim = dim

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = tokenize(text)
        features = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
        for feat in features:
            digest = hashlib.blake2b(feat.encode(), digest_size=8).digest()
            idx = int.from_bytes(digest[:4], "little") % self.dim
            sign = 1.0 if digest[4] & 1 else -1.0
            vec[idx] += sign * (1.5 if "_" in feat else 1.0)
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]


class OpenAIEmbedder:
    name = "openai-text-embedding-3-small"

    def __init__(self, api_key: str, dim: int) -> None:
        self.api_key = api_key
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        resp = httpx.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": "text-embedding-3-small", "input": texts, "dimensions": self.dim},
            timeout=30,
        )
        resp.raise_for_status()
        return [row["embedding"] for row in resp.json()["data"]]


@lru_cache
def get_embedder() -> Embedder:
    s = get_settings()
    if s.embedding_provider == "openai" and s.openai_api_key:
        return OpenAIEmbedder(s.openai_api_key, s.embedding_dim)
    return HashingEmbedder(s.embedding_dim)


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)
