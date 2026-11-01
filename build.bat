@echo off
rem Gera dist\lng_converter.exe (um arquivo so, com o Python embutido). Requer: pip install pyinstaller
cd /d %~dp0
python -m PyInstaller --onefile --windowed --noconfirm --clean --name lng_converter --icon assets\icon.ico --add-data "assets\icon.ico;assets" lng_converter_gui.py
