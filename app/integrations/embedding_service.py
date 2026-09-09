"""Local multilingual text embeddings.

The dependency and model are optional at application startup. This keeps the
existing JSON/LLM flow usable in environments where model packages or model
weights have not been installed yet.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Sequence
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class EmbeddingService:
    """Encode text and compare embeddings with cosine similarity.

    Model loading is lazy: constructing the service never downloads weights.
    If loading fails, ``available`` is false and embedding operations return
    ``None`` instead of breaking the resume pipeline.
    """

    def __init__(
        self,
        enabled: bool | None = None,
        model_name: str | None = None,
        model: Any | None = None,
    ) -> None:
        settings = get_settings()
        self.enabled = settings.embedding_enabled if enabled is None else enabled
        self.model_name = model_name or settings.embedding_model_name or DEFAULT_MODEL_NAME
        self._model = model
        self._load_attempted = model is not None
        self.last_error: str | None = None

    @property
    def available(self) -> bool:
        """Whether the service is enabled and has a usable model."""
        if not self.enabled:
            return False
        self._ensure_model()
        return self._model is not None

    def embed(self, text: str) -> list[float] | None:
        """Return an L2-normalized embedding, or ``None`` when unavailable."""
        if not self.enabled or not isinstance(text, str) or not text.strip():
            return None
        if not self._ensure_model():
            return None

        try:
            encoded = self._model.encode(text, convert_to_numpy=False)
            vector = [float(value) for value in encoded]
            return self.normalize(vector)
        except Exception as error:  # noqa: BLE001 - model backends expose varied errors
            self.last_error = str(error)
            logger.warning("Embedding failed for model %s: %s", self.model_name, error)
            return None

    def cosine_similarity(
        self, left: Sequence[float] | None, right: Sequence[float] | None
    ) -> float | None:
        """Calculate cosine similarity for two vectors.

        Returns ``None`` for missing, empty, mismatched, or zero vectors.
        Inputs do not need to be normalized.
        """
        if left is None or right is None or len(left) == 0 or len(left) != len(right):
            return None
        left_norm = math.sqrt(sum(float(value) ** 2 for value in left))
        right_norm = math.sqrt(sum(float(value) ** 2 for value in right))
        if left_norm == 0 or right_norm == 0:
            return None
        dot = sum(float(a) * float(b) for a, b in zip(left, right))
        return dot / (left_norm * right_norm)

    @staticmethod
    def normalize(vector: Sequence[float]) -> list[float]:
        """Return an L2-normalized copy of a vector."""
        values = [float(value) for value in vector]
        norm = math.sqrt(sum(value**2 for value in values))
        if norm == 0:
            return values
        return [value / norm for value in values]

    def _ensure_model(self) -> bool:
        if self._model is not None:
            return True
        if self._load_attempted:
            return False
        self._load_attempted = True
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
            return True
        except Exception as error:  # noqa: BLE001 - import/download/backend errors vary
            self.last_error = str(error)
            logger.warning(
                "Embedding model %s is unavailable: %s", self.model_name, error
            )
            return False
