@echo off
setlocal
cd /d "%~dp0"
echo Local Narration - starting up...
echo Checking this PC. This can take a moment; progress appears below.
if not exist "app\static\ui\build-info.json" (
  echo Application interface is missing. Re-extract the complete sharing ZIP.
  echo Developers: run npm.cmd ci and npm.cmd run build inside frontend first.
  pause
  exit /b 1
)
if not exist ".venv-qwen3\Scripts\python.exe" (
  echo Application environment not found. Follow README.md.
  pause
  exit /b 1
)
".venv-qwen3\Scripts\python.exe" -u scripts\check_local_setup.py
if errorlevel 1 (
  pause
  exit /b 1
)
echo Starting Local Narration. Open http://127.0.0.1:8000 when the server is ready.
echo Keep this window open. Press Ctrl+C to stop the app.
".venv-qwen3\Scripts\python.exe" -u scripts\serve.py
if errorlevel 1 pause
