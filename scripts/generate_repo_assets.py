from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from sticky_brain.app import MainWindow
from sticky_brain.models import Note
from sticky_brain.organizer import NoteOrganizer
from sticky_brain.widgets import NoteEditorDialog


ASSETS_DIR = ROOT / "assets"
ASSETS_DIR.mkdir(exist_ok=True)


def populate_sample_notes(window: MainWindow) -> None:
    organizer = NoteOrganizer()
    samples = [
        """Service Principal: billing-prod-sp
Client ID: 11111111-2222-3333-4444-555555555555
AD Group: Billing-Prod-Readers
Pending - rotate next week
#azure #billing""",
        """API key for sandbox partner integration
Owner: integrations
Use for smoke tests only
Expires next month
#api #sandbox""",
        """Follow up with IAM team about reader access
Need ad group for analytics-prod
Reminder: ask before Friday
#access""",
        """VPN hostname: corp-vpn-gateway-02
Subscription: Prod-Network
Firewall note: allow vendor IP by Tuesday
#infra #network""",
        """Tenant ID: 99999999-aaaa-bbbb-cccc-123456789012
App Name: Reporting Automation
Role: Storage Blob Reader
Done after access validation
#identity""",
    ]

    for raw_text in samples:
        note = Note()
        organizer.apply_to_note(note, raw_text)
        window._save_note(note)

    window.refresh_notes()


def render_assets() -> None:
    temp_dir = Path(tempfile.mkdtemp(prefix="sticky_brain_assets_"))
    try:
        os.environ["STICKY_BRAIN_DB_PATH"] = str(temp_dir / "preview.db")

        app = QApplication([])
        window = MainWindow()
        populate_sample_notes(window)
        window.resize(1440, 980)
        window.show()
        app.processEvents()
        QTimer.singleShot(300, app.quit)
        app.exec()
        app.processEvents()
        window.grab().save(str(ASSETS_DIR / "screenshot-board.png"))

        note = window.filtered_notes[0]
        dialog = NoteEditorDialog(note, window.organizer)
        dialog.resize(560, 700)
        dialog.show()
        app.processEvents()
        QTimer.singleShot(300, app.quit)
        app.exec()
        app.processEvents()
        dialog.grab().save(str(ASSETS_DIR / "screenshot-editor.png"))

        dialog.close()
        window.close()
        app.quit()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    render_assets()
