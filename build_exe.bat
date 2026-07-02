@echo off
setlocal
cd /d "%~dp0"
python -m pip install -r requirements.txt
python -m pip install -r requirements-build.txt
python -m PyInstaller --noconfirm --windowed --name Giflet app.py
echo.
echo EXE created at dist\Giflet\Giflet.exe
