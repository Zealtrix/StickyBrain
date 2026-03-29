from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from sticky_brain.models import Note
from sticky_brain.organizer import NoteOrganizer

PALETTE = ["#FFF4A3", "#FFD8B1", "#D9F99D", "#BFDBFE", "#F5D0FE", "#FECACA"]


class NoteCard(QFrame):
    def __init__(self, note: Note, selected: bool, on_click) -> None:
        super().__init__()
        self.note = note
        self._on_click = on_click
        self.setObjectName("NoteCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumWidth(220)
        self.setMaximumWidth(260)
        self.setStyleSheet(self._build_style(selected))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)

        ribbon = QLabel(note.category or "General")
        ribbon.setStyleSheet("font-size: 11px; font-weight: 700; color: #7c2d12; text-transform: uppercase;")
        layout.addWidget(ribbon)

        title = QLabel(note.title or "Untitled")
        title.setWordWrap(True)
        title.setStyleSheet("font-size: 17px; font-weight: 700; color: #1f2937;")
        layout.addWidget(title)

        preview = QLabel(note.preview)
        preview.setWordWrap(True)
        preview.setStyleSheet("font-size: 14px; color: #374151;")
        layout.addWidget(preview)

        meta_bits = []
        if note.tags:
            meta_bits.append("#" + "  #".join(note.tags[:3]))
        if note.sensitive:
            meta_bits.append("Sensitive")
        if note.status == "done":
            meta_bits.append("Done")
        meta = QLabel(" | ".join(meta_bits) if meta_bits else "Freeform sticky")
        meta.setWordWrap(True)
        meta.setStyleSheet("font-size: 12px; color: #4b5563;")
        layout.addWidget(meta)

        if note.pinned:
            pin = QLabel("Pinned")
            pin.setStyleSheet("font-size: 11px; font-weight: 700; color: #7c2d12;")
            layout.addWidget(pin)

        layout.addStretch(1)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            self._on_click(self.note.id)
        super().mousePressEvent(event)

    def _build_style(self, selected: bool) -> str:
        border = "#C2410C" if selected else "#D1D5DB"
        ring = "#FFFBEB" if selected else self.note.color
        return f"""
        QFrame#NoteCard {{
            background-color: {self.note.color};
            border: 2px solid {border};
            border-radius: 18px;
        }}
        QFrame#NoteCard:hover {{
            border-color: #9A3412;
            background-color: {ring};
        }}
        """


class NoteEditorDialog(QDialog):
    def __init__(self, note: Note, organizer: NoteOrganizer, parent=None) -> None:
        super().__init__(parent)
        self.note = Note(
            id=note.id,
            title=note.title,
            body=note.body,
            tags=list(note.tags),
            category=note.category,
            status=note.status,
            pinned=note.pinned,
            sensitive=note.sensitive,
            color=note.color,
            created_at=note.created_at,
            updated_at=note.updated_at,
            embedding_json=note.embedding_json,
            embedding_hash=note.embedding_hash,
        )
        self.organizer = organizer

        self.setWindowTitle("Sticky")
        self.resize(520, 640)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Sticky")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #0f172a;")
        layout.addWidget(title)

        self.title_input = QLineEdit(self.note.title)
        self.title_input.setPlaceholderText("Title")
        layout.addWidget(self.title_input)

        self.body_input = QTextEdit()
        self.body_input.setPlainText(self.note.body)
        self.body_input.setPlaceholderText("Paste or edit the sticky content here...")
        layout.addWidget(self.body_input, 1)

        chips = QWidget()
        chips_layout = QHBoxLayout(chips)
        chips_layout.setContentsMargins(0, 0, 0, 0)
        chips_layout.setSpacing(10)

        self.category_input = QLineEdit(self.note.category)
        self.category_input.setPlaceholderText("Category")
        chips_layout.addWidget(self.category_input)

        self.tags_input = QLineEdit(self.note.tags_text)
        self.tags_input.setPlaceholderText("tag1, tag2")
        chips_layout.addWidget(self.tags_input)
        layout.addWidget(chips)

        flags = QWidget()
        flags_layout = QHBoxLayout(flags)
        flags_layout.setContentsMargins(0, 0, 0, 0)
        flags_layout.setSpacing(12)

        self.status_input = QComboBox()
        self.status_input.addItems(["pending", "done"])
        self.status_input.setCurrentText(self.note.status)
        flags_layout.addWidget(self.status_input)

        self.color_input = QComboBox()
        self.color_input.addItems(PALETTE)
        self.color_input.setCurrentText(self.note.color)
        flags_layout.addWidget(self.color_input)

        self.pinned_input = QCheckBox("Pinned")
        self.pinned_input.setChecked(self.note.pinned)
        flags_layout.addWidget(self.pinned_input)

        self.sensitive_input = QCheckBox("Sensitive")
        self.sensitive_input.setChecked(self.note.sensitive)
        flags_layout.addWidget(self.sensitive_input)
        flags_layout.addStretch(1)
        layout.addWidget(flags)

        self.preview_label = QLabel("")
        self.preview_label.setWordWrap(True)
        self.preview_label.setStyleSheet("color: #475569; font-size: 13px;")
        layout.addWidget(self.preview_label)

        buttons = QHBoxLayout()
        organize_button = QPushButton("Organize from text")
        organize_button.clicked.connect(self.apply_organizer)
        buttons.addWidget(organize_button)

        buttons.addStretch(1)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(cancel_button)

        save_button = QPushButton("Save Sticky")
        save_button.clicked.connect(self.accept)
        buttons.addWidget(save_button)
        layout.addLayout(buttons)

        self.body_input.textChanged.connect(self._refresh_preview)
        self._refresh_preview()

    def apply_organizer(self) -> None:
        organized = self.organizer.organize(self.body_input.toPlainText())
        self.title_input.setText(organized.title)
        self.category_input.setText(organized.category)
        self.tags_input.setText(", ".join(organized.tags))
        self.status_input.setCurrentText(organized.status)
        self.color_input.setCurrentText(organized.color)
        self.sensitive_input.setChecked(organized.sensitive)
        if organized.pinned:
            self.pinned_input.setChecked(True)
        self._refresh_preview()

    def updated_note(self) -> Note:
        self.note.title = self.title_input.text().strip()
        self.note.body = self.body_input.toPlainText().strip()
        self.note.category = self.category_input.text().strip()
        self.note.tags = Note.normalize_tags(self.tags_input.text())
        self.note.status = self.status_input.currentText()
        self.note.color = self.color_input.currentText()
        self.note.pinned = self.pinned_input.isChecked()
        self.note.sensitive = self.sensitive_input.isChecked()
        return self.note

    def _refresh_preview(self) -> None:
        organized = self.organizer.organize(self.body_input.toPlainText())
        preview = f"Organizer preview: {organized.category} | {organized.status} | {', '.join(organized.tags[:4]) or 'no tags'}"
        if organized.sensitive:
            preview += " | sensitive"
        self.preview_label.setText(preview)
