from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Iterable

from sticky_brain.models import Note

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass(slots=True)
class SearchResult:
    note: Note
    score: float


class SearchEngine:
    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        self.model_name = model_name
        self.semantic_available = False
        self.status = "Keyword search ready. Semantic search will activate when the tiny local model is available."
        self._embedder = None

        try:
            from fastembed import TextEmbedding

            self._embedder = TextEmbedding(model_name=model_name)
            self.semantic_available = True
            self.status = f"Semantic search ready with local model: {model_name}"
        except Exception as exc:
            self.status = f"Keyword search only. Semantic model unavailable: {exc}"

    @staticmethod
    def content_hash(note: Note) -> str:
        return hashlib.sha256(note.search_text.encode("utf-8")).hexdigest()

    def ensure_embedding(self, note: Note) -> bool:
        if not self.semantic_available or self._embedder is None:
            return False

        current_hash = self.content_hash(note)
        if note.embedding_json and note.embedding_hash == current_hash:
            return False

        vector = next(self._embedder.embed([note.search_text]))
        note.embedding_json = json.dumps([float(value) for value in vector])
        note.embedding_hash = current_hash
        return True

    def search(
        self,
        notes: Iterable[Note],
        query: str,
        mode: str = "Hybrid",
        status_filter: str = "All",
    ) -> list[SearchResult]:
        filtered = [note for note in notes if self._matches_status(note, status_filter)]
        trimmed_query = query.strip()

        if not trimmed_query:
            ordered = sorted(filtered, key=self._default_sort_key, reverse=True)
            return [SearchResult(note=note, score=0.0) for note in ordered]

        keyword_scores = {note.id: self._keyword_score(note, trimmed_query) for note in filtered}
        semantic_scores = (
            self._semantic_scores(filtered, trimmed_query)
            if mode in {"Hybrid", "Semantic"} and self.semantic_available
            else {}
        )

        results: list[SearchResult] = []
        for note in filtered:
            keyword = keyword_scores.get(note.id, 0.0)
            semantic = semantic_scores.get(note.id, 0.0)

            if mode == "Keyword":
                score = keyword
            elif mode == "Semantic":
                score = semantic
            else:
                score = (keyword * 0.55) + (semantic * 0.45)

            if score > 0:
                results.append(SearchResult(note=note, score=score))

        results.sort(key=lambda item: (item.note.pinned, item.score, item.note.updated_at), reverse=True)
        return results

    def _semantic_scores(self, notes: list[Note], query: str) -> dict[str, float]:
        if not self.semantic_available or self._embedder is None:
            return {}

        query_vector = [float(value) for value in next(self._embedder.embed([query]))]
        scores: dict[str, float] = {}

        for note in notes:
            if not note.embedding_json:
                continue
            note_vector = json.loads(note.embedding_json)
            score = self._cosine_similarity(query_vector, note_vector)
            if score > 0.2:
                scores[note.id] = score

        return scores

    @staticmethod
    def _keyword_score(note: Note, query: str) -> float:
        haystack = f"{note.title}\n{note.body}\n{note.category}\n{' '.join(note.tags)}".lower()
        words = [word for word in query.lower().split() if word]
        if not words:
            return 0.0

        score = 0.0
        for word in words:
            count = haystack.count(word)
            if count == 0:
                continue
            if note.title.lower().count(word):
                score += 3.0
            score += 1.2 * count

        if query.lower() in haystack:
            score += 2.0
        return score

    @staticmethod
    def _matches_status(note: Note, status_filter: str) -> bool:
        if status_filter == "All":
            return True
        return note.status.lower() == status_filter.lower()

    @staticmethod
    def _default_sort_key(note: Note) -> tuple[int, str]:
        return (1 if note.pinned else 0, note.updated_at)

    @staticmethod
    def _cosine_similarity(first: list[float], second: list[float]) -> float:
        if len(first) != len(second):
            return 0.0

        dot = sum(left * right for left, right in zip(first, second))
        left_mag = math.sqrt(sum(value * value for value in first))
        right_mag = math.sqrt(sum(value * value for value in second))
        if left_mag == 0 or right_mag == 0:
            return 0.0
        return dot / (left_mag * right_mag)
