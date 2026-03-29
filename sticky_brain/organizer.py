from __future__ import annotations

import re
from dataclasses import dataclass

from sticky_brain.models import Note

CATEGORY_COLORS = {
    "Identity": "#BFDBFE",
    "Secrets": "#FECACA",
    "Tasks": "#FFF4A3",
    "Infra": "#FFD8B1",
    "Access": "#D9F99D",
    "General": "#F5D0FE",
}

HASHTAG_PATTERN = re.compile(r"#([\w-]+)")
KEY_VALUE_PATTERN = re.compile(r"^\s*([A-Za-z][A-Za-z0-9 /_-]{1,30})\s*[:=-]\s*(.+)$")
LONG_TOKEN_PATTERN = re.compile(r"\b[A-Za-z0-9_\-=/+]{24,}\b")

CATEGORY_RULES = [
    ("Identity", ("service principal", "spn", "entra", "aad", "azure ad", "tenant id", "client id", "ad group")),
    ("Secrets", ("api key", "token", "password", "secret", "sas", "private key", "connection string")),
    ("Tasks", ("todo", "pending", "follow up", "need to", "action item", "next step", "remind")),
    ("Infra", ("server", "hostname", "vm", "firewall", "vpn", "subnet", "dns", "cluster", "namespace")),
    ("Access", ("role", "permission", "access", "reader", "contributor", "owner", "group")),
]

TAG_RULES = {
    "service principal": "spn",
    "client id": "client-id",
    "client secret": "client-secret",
    "tenant id": "tenant",
    "api key": "api-key",
    "token": "token",
    "secret": "secret",
    "ad group": "group",
    "entra": "entra",
    "aad": "entra",
    "azure": "azure",
    "prod": "prod",
    "production": "prod",
    "dev": "dev",
    "uat": "uat",
    "qa": "qa",
    "firewall": "firewall",
    "vpn": "vpn",
    "subscription": "subscription",
    "pending": "pending",
    "todo": "todo",
}

DONE_WORDS = ("done", "completed", "closed", "resolved", "finished")
URGENT_WORDS = ("urgent", "asap", "critical", "today", "prod issue", "production issue")
SENSITIVE_WORDS = (
    "api key",
    "token",
    "secret",
    "password",
    "private key",
    "client secret",
    "connection string",
    "sas",
)


@dataclass(slots=True)
class OrganizedNote:
    title: str
    body: str
    tags: list[str]
    category: str
    status: str
    sensitive: bool
    pinned: bool
    color: str


class NoteOrganizer:
    def organize(self, raw_text: str) -> OrganizedNote:
        body = self._normalize_body(raw_text)
        lowered = body.lower()
        category = self._detect_category(lowered)
        status = self._detect_status(lowered)
        sensitive = self._detect_sensitive(lowered, body)
        pinned = any(word in lowered for word in URGENT_WORDS)
        title = self._derive_title(body, category, sensitive)
        tags = self._extract_tags(body, lowered, category, status)
        color = CATEGORY_COLORS.get(category, CATEGORY_COLORS["General"])
        return OrganizedNote(
            title=title,
            body=body,
            tags=tags,
            category=category,
            status=status,
            sensitive=sensitive,
            pinned=pinned,
            color=color,
        )

    def apply_to_note(self, note: Note, raw_text: str) -> Note:
        organized = self.organize(raw_text)
        note.title = organized.title
        note.body = organized.body
        note.tags = organized.tags
        note.category = organized.category
        note.status = organized.status
        note.sensitive = organized.sensitive
        note.pinned = organized.pinned or note.pinned
        note.color = organized.color
        return note

    def _normalize_body(self, raw_text: str) -> str:
        lines = [line.rstrip() for line in raw_text.replace("\r\n", "\n").split("\n")]
        cleaned: list[str] = []
        last_blank = False
        for line in lines:
            stripped = line.strip()
            if not stripped:
                if not last_blank and cleaned:
                    cleaned.append("")
                last_blank = True
                continue
            cleaned.append(stripped)
            last_blank = False
        return "\n".join(cleaned).strip()

    def _detect_category(self, lowered: str) -> str:
        for category, keywords in CATEGORY_RULES:
            if any(keyword in lowered for keyword in keywords):
                return category
        return "General"

    def _detect_status(self, lowered: str) -> str:
        if any(word in lowered for word in DONE_WORDS):
            return "done"
        return "pending"

    def _detect_sensitive(self, lowered: str, body: str) -> bool:
        if any(word in lowered for word in SENSITIVE_WORDS):
            return True
        return bool(LONG_TOKEN_PATTERN.search(body))

    def _extract_tags(self, body: str, lowered: str, category: str, status: str) -> list[str]:
        tags = Note.normalize_tags(HASHTAG_PATTERN.findall(body))
        for phrase, tag in TAG_RULES.items():
            if phrase in lowered:
                tags.append(tag)
        tags.append(category.lower())
        if status == "pending":
            tags.append("pending")
        return Note.normalize_tags(tags)[:8]

    def _derive_title(self, body: str, category: str, sensitive: bool) -> str:
        lines = [line for line in body.splitlines() if line.strip()]
        for line in lines:
            match = KEY_VALUE_PATTERN.match(line)
            if not match:
                continue
            key = match.group(1).strip()
            value = self._clean_title_value(match.group(2))
            key_lower = key.lower()

            if "group" in key_lower and value:
                return value
            if "service principal" in key_lower and value and not self._looks_sensitive(value):
                return f"Service principal: {value}"
            if any(word in key_lower for word in ("name", "app", "system", "service")) and value and not self._looks_sensitive(value):
                return value
            if not sensitive and value and len(value) <= 56 and not self._looks_sensitive(value):
                return f"{key.title()}: {value}"
            return key.title()

        if lines:
            first_line = re.sub(r"^(todo|pending|follow up|follow-up|task)\s*[:\-]\s*", "", lines[0], flags=re.I)
            first_line = self._clean_title_value(first_line)
            if first_line:
                return first_line[:56]

        fallback_titles = {
            "Identity": "Identity sticky",
            "Secrets": "Credential sticky",
            "Tasks": "Follow-up sticky",
            "Infra": "Infra sticky",
            "Access": "Access sticky",
        }
        return fallback_titles.get(category, "Quick sticky")

    @staticmethod
    def _clean_title_value(value: str) -> str:
        value = value.strip().strip("-")
        value = re.sub(r"\s+", " ", value)
        return value[:72]

    @staticmethod
    def _looks_sensitive(value: str) -> bool:
        lowered = value.lower()
        if any(word in lowered for word in SENSITIVE_WORDS):
            return True
        return bool(LONG_TOKEN_PATTERN.search(value))
