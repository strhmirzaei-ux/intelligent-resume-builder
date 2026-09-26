"""Small FAISS adapter for searching JSON-stored embeddings."""

from __future__ import annotations

import math
from typing import Any, Sequence


def search_rows(
    rows: Sequence[Any],
    embedding: list[float],
    limit: int,
) -> list[tuple[Any, float]]:
    """Return the nearest rows using cosine similarity via FAISS inner product."""
    if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
        return []

    try:
        query_values = [float(value) for value in embedding]
    except (TypeError, ValueError):
        return []
    if not query_values or not all(math.isfinite(value) for value in query_values):
        return []

    candidates: list[Any] = []
    vectors_as_lists: list[list[float]] = []
    for row in rows:
        raw_vector = getattr(row, "embedding", None)
        if raw_vector is None or isinstance(raw_vector, (str, bytes)):
            continue
        try:
            vector = [float(value) for value in raw_vector]
        except (TypeError, ValueError):
            continue
        if (
            len(vector) != len(query_values)
            or not vector
            or not all(math.isfinite(value) for value in vector)
            or math.sqrt(sum(value**2 for value in vector)) == 0
        ):
            continue
        candidates.append(row)
        vectors_as_lists.append(vector)

    if not candidates:
        return []

    try:
        import faiss
        import numpy as np
    except ImportError as error:  # pragma: no cover - exercised in deployment
        raise RuntimeError(
            "FAISS is required for vector search. Install it with: pip install faiss-cpu"
        ) from error

    query = np.asarray([query_values], dtype="float32")
    vectors = np.asarray(vectors_as_lists, dtype="float32")
    if vectors.ndim != 2 or query.ndim != 2 or vectors.shape[1] != query.shape[1]:
        return []
    if not np.isfinite(vectors).all() or not np.isfinite(query).all():
        return []
    if float(np.linalg.norm(query)) == 0:
        return []

    faiss.normalize_L2(vectors)
    faiss.normalize_L2(query)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    scores, indexes = index.search(query, min(limit, len(candidates)))
    return [
        (candidates[int(index)], float(score))
        for index, score in zip(indexes[0], scores[0])
        if index >= 0
    ]
