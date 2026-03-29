@echo off
cd /d "%~dp0"
python -m PyInstaller --noconfirm StickyBrain.spec
"%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" installer.iss
