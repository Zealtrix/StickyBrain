from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStatusBar,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from sticky_brain.models import Note
from sticky_brain.organizer import NoteOrganizer
from sticky_brain.search import SearchEngine
from sticky_brain.storage import NoteRepository, app_storage_dir, default_db_path
from sticky_brain.widgets import NoteCard, NoteEditorDialog

APP_TITLE = "Sticky Brain"
CARD_WIDTH = 250


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1420, 900)

        self.repo = NoteRepository(default_db_path())
        self.search_engine = SearchEngine()
        self.organizer = NoteOrganizer()
        self.notes = self.repo.list_notes()
        self.filtered_notes = list(self.notes)
        self.selected_note_id: str | None = self.notes[0].id if self.notes else None

        self._build_ui()
        self._build_menu()
        self.refresh_notes()

    def _build_ui(self) -> None:
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(12, 12, 12, 12)
        root_layout.setSpacing(12)

        title = QLabel("Sticky Brain")
        title.setStyleSheet("font-size: 28px; font-weight: 800; color: #0f172a;")
        root_layout.addWidget(title)

        subtitle = QLabel("Paste first. The app turns rough text into organized sticky notes you can search later.")
        subtitle.setStyleSheet("color: #475569; font-size: 14px;")
        subtitle.setWordWrap(True)
        root_layout.addWidget(subtitle)

        capture_frame = QFrame()
        capture_frame.setObjectName("CaptureFrame")
        capture_layout = QVBoxLayout(capture_frame)
        capture_layout.setContentsMargins(18, 18, 18, 18)
        capture_layout.setSpacing(12)

        capture_title = QLabel("Quick Capture")
        capture_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #0f172a;")
        capture_layout.addWidget(capture_title)

        self.capture_input = QTextEdit()
        self.capture_input.setPlaceholderText(
            "Paste anything here: API key context, service principal details, AD group name, follow-up task, reminder..."
        )
        self.capture_input.setMinimumHeight(140)
        self.capture_input.textChanged.connect(self.update_capture_preview)
        capture_layout.addWidget(self.capture_input)

        self.capture_preview = QLabel("Organizer preview will appear here after you paste.")
        self.capture_preview.setWordWrap(True)
        self.capture_preview.setStyleSheet("color: #475569; font-size: 13px;")
        capture_layout.addWidget(self.capture_preview)

        capture_buttons = QHBoxLayout()
        capture_buttons.setSpacing(10)

        organize_button = QPushButton("Paste and Save Sticky")
        organize_button.clicked.connect(self.create_note_from_capture)
        capture_buttons.addWidget(organize_button)

        blank_button = QPushButton("Blank Sticky")
        blank_button.clicked.connect(self.create_blank_note)
        capture_buttons.addWidget(blank_button)

        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.capture_input.clear)
        capture_buttons.addWidget(clear_button)
        capture_buttons.addStretch(1)
        capture_layout.addLayout(capture_buttons)

        root_layout.addWidget(capture_frame)

        controls = QHBoxLayout()
        controls.setSpacing(10)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search notes, secrets, group names, tasks, APIs...")
        self.search_input.textChanged.connect(self.refresh_notes)
        controls.addWidget(self.search_input, 1)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["All", "Pending", "Done"])
        self.status_filter.currentTextChanged.connect(self.refresh_notes)
        controls.addWidget(self.status_filter)

        self.search_mode = QComboBox()
        self.search_mode.addItems(["Hybrid", "Keyword", "Semantic"])
        self.search_mode.currentTextChanged.connect(self.refresh_notes)
        controls.addWidget(self.search_mode)

        duplicate_button = QPushButton("Duplicate")
        duplicate_button.clicked.connect(self.duplicate_note)
        controls.addWidget(duplicate_button)

        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(self.delete_current_note)
        controls.addWidget(delete_button)

        reindex_button = QPushButton("Reindex Search")
        reindex_button.clicked.connect(self.reindex_notes)
        controls.addWidget(reindex_button)

        root_layout.addLayout(controls)

        helper = QLabel("Click any sticky to edit it. Search stays local and uses SQLite plus a tiny semantic model.")
        helper.setWordWrap(True)
        helper.setStyleSheet("color: #475569; font-size: 13px;")
        root_layout.addWidget(helper)

        self.results_label = QLabel()
        self.results_label.setStyleSheet("font-weight: 600; color: #0f172a;")
        root_layout.addWidget(self.results_label)

        self.board_scroll = QScrollArea()
        self.board_scroll.setWidgetResizable(True)
        self.board_scroll.setFrameShape(QFrame.NoFrame)
        self.board_scroll.viewport().installEventFilter(self)

        self.board_widget = QWidget()
        self.board_layout = QGridLayout(self.board_widget)
        self.board_layout.setContentsMargins(4, 4, 4, 4)
        self.board_layout.setHorizontalSpacing(12)
        self.board_layout.setVerticalSpacing(12)
        self.board_scroll.setWidget(self.board_widget)
        root_layout.addWidget(self.board_scroll, 1)

        status = QStatusBar()
        self.setStatusBar(status)
        self.statusBar().showMessage(self.search_engine.status)
        self.statusBar().showMessage(f"{self.search_engine.status} | Data: {app_storage_dir()}", 10000)

        self.setCentralWidget(root)
        self.setStyleSheet(
            """
            QWidget {
                background-color: #F8FAFC;
                color: #0F172A;
                font-size: 14px;
            }
            QFrame#CaptureFrame {
                background-color: #FEF3C7;
                border: 1px solid #F59E0B;
                border-radius: 24px;
            }
            QLineEdit, QTextEdit, QComboBox {
                background: white;
                border: 1px solid #CBD5E1;
                border-radius: 12px;
                padding: 8px 10px;
            }
            QPushButton {
                background: #0F766E;
                color: white;
                border: none;
                border-radius: 12px;
                padding: 10px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #115E59;
            }
            """
        )

    def _build_menu(self) -> None:
        new_action = QAction("New Sticky", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.create_blank_note)
        self.addAction(new_action)

        save_action = QAction("Paste and Save Sticky", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.create_note_from_capture)
        self.addAction(save_action)

        find_action = QAction("Focus Search", self)
        find_action.setShortcut("Ctrl+F")
        find_action.triggered.connect(self.search_input.setFocus)
        self.addAction(find_action)

    def eventFilter(self, watched, event) -> bool:  # noqa: N802
        if watched is self.board_scroll.viewport() and event.type() == QEvent.Type.Resize:
            self._render_board()
        return super().eventFilter(watched, event)

    def refresh_notes(self) -> None:
        self.notes = self.repo.list_notes()
        results = self.search_engine.search(
            self.notes,
            self.search_input.text(),
            self.search_mode.currentText(),
            self.status_filter.currentText(),
        )
        self.filtered_notes = [result.note for result in results]
        self.results_label.setText(f"{len(self.filtered_notes)} notes")

        if self.selected_note_id and all(note.id != self.selected_note_id for note in self.notes):
            self.selected_note_id = self.filtered_notes[0].id if self.filtered_notes else None

        self._render_board()

    def _render_board(self) -> None:
        while self.board_layout.count():
            item = self.board_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        width = max(self.board_scroll.viewport().width(), CARD_WIDTH)
        columns = max(1, width // (CARD_WIDTH + 18))

        for index, note in enumerate(self.filtered_notes):
            row = index // columns
            column = index % columns
            card = NoteCard(note, note.id == self.selected_note_id, self.open_note)
            self.board_layout.addWidget(card, row, column)

        self.board_layout.setRowStretch(max(1, (len(self.filtered_notes) // columns) + 1), 1)
        self.board_layout.setColumnStretch(columns, 1)

    def current_note(self) -> Note | None:
        if not self.selected_note_id:
            return None
        return self.repo.get_note(self.selected_note_id)

    def update_capture_preview(self) -> None:
        raw_text = self.capture_input.toPlainText().strip()
        if not raw_text:
            self.capture_preview.setText("Organizer preview will appear here after you paste.")
            return

        organized = self.organizer.organize(raw_text)
        summary = f"Will save as: {organized.title} | {organized.category} | {', '.join(organized.tags[:5]) or 'no tags'}"
        if organized.sensitive:
            summary += " | sensitive"
        self.capture_preview.setText(summary)

    def create_note_from_capture(self) -> None:
        raw_text = self.capture_input.toPlainText().strip()
        if not raw_text:
            QMessageBox.information(self, "Nothing to save", "Paste some text into Quick Capture first.")
            return

        note = Note()
        self.organizer.apply_to_note(note, raw_text)
        self._save_note(note)
        self.selected_note_id = note.id
        self.capture_input.clear()
        self.capture_preview.setText("Organizer preview will appear here after you paste.")
        self.refresh_notes()
        self.statusBar().showMessage(f"Saved '{note.title}'", 4000)

    def create_blank_note(self) -> None:
        note = Note(title="Quick sticky", body="", category="General", color="#FFF4A3")
        dialog = NoteEditorDialog(note, self.organizer, self)
        if dialog.exec():
            saved = dialog.updated_note()
            if not saved.title.strip() and not saved.body.strip():
                return
            self._save_note(saved)
            self.selected_note_id = saved.id
            self.refresh_notes()

    def duplicate_note(self) -> None:
        original = self.current_note()
        if original is None:
            QMessageBox.information(self, "Select a sticky", "Open a sticky first, then duplicate it.")
            return

        clone = Note(
            title=f"{original.title} Copy".strip(),
            body=original.body,
            tags=list(original.tags),
            category=original.category,
            status=original.status,
            pinned=original.pinned,
            sensitive=original.sensitive,
            color=original.color,
        )
        self._save_note(clone)
        self.selected_note_id = clone.id
        self.refresh_notes()

    def delete_current_note(self) -> None:
        note = self.current_note()
        if note is None:
            QMessageBox.information(self, "Select a sticky", "Open a sticky first, then delete it.")
            return

        answer = QMessageBox.question(
            self,
            "Delete Sticky",
            f"Delete '{note.title or 'Untitled'}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer != QMessageBox.Yes:
            return

        self.repo.delete(note.id)
        self.selected_note_id = None
        self.refresh_notes()
        if self.filtered_notes:
            self.selected_note_id = self.filtered_notes[0].id
            self._render_board()

    def open_note(self, note_id: str) -> None:
        note = self.repo.get_note(note_id)
        if note is None:
            return

        self.selected_note_id = note_id
        self._render_board()

        dialog = NoteEditorDialog(note, self.organizer, self)
        if dialog.exec():
            updated = dialog.updated_note()
            self._save_note(updated)
            self.refresh_notes()
            self.statusBar().showMessage(f"Saved '{updated.title or 'Untitled'}'", 3500)

    def reindex_notes(self) -> None:
        indexed = 0
        for note in self.repo.list_notes():
            if self.search_engine.ensure_embedding(note):
                self.repo.upsert(note)
                indexed += 1
        self.refresh_notes()
        self.statusBar().showMessage(f"Reindexed {indexed} notes", 5000)

    def _save_note(self, note: Note) -> None:
        if self.search_engine.ensure_embedding(note):
            self.statusBar().showMessage(self.search_engine.status, 4000)
        self.repo.upsert(note)

    def closeEvent(self, event) -> None:  # noqa: N802
        self.repo.close()
        event.accept()


def run() -> None:
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
