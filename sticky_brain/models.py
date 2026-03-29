from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable
from uuid import uuid4


def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat()


@dataclass(slots=True)
class Note:
    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = ""
    body: str = ""
    tags: list[str] = field(default_factory=list)
    category: str = ""
    status: str = "pending"
    pinned: bool = False
    sensitive: bool = False
    color: str = "#FFF4A3"
    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)
    embedding_json: str | None = None
    embedding_hash: str | None = None

    @property
    def preview(self) -> str:
        text = self.body.strip().replace("\n", " ")
        if not text:
            return "Empty note"
        return text[:140] + ("..." if len(text) > 140 else "")

    @property
    def search_text(self) -> str:
        parts = [self.title, self.body, self.category, " ".join(self.tags), self.status]
        return "\n".join(part for part in parts if part).strip()

    @property
    def tags_text(self) -> str:
        return ", ".join(self.tags)

    @classmethod
    def normalize_tags(cls, raw_tags: str | Iterable[str]) -> list[str]:
        if isinstance(raw_tags, str):
            parts = raw_tags.split(",")
        else:
            parts = list(raw_tags)
        clean: list[str] = []
        seen: set[str] = set()
        for part in parts:
            tag = str(part).strip()
            lowered = tag.lower()
            if not tag or lowered in seen:
                continue
            seen.add(lowered)
            clean.append(tag)
        return clean
