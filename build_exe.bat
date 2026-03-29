@echo off
cd /d "%~dp0"
python -m PyInstaller --noconfirm StickyBrain.spec
