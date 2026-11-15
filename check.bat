@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv-chatterbox\Scripts\python.exe" (
  echo Application environment not found.
  echo Follow the setup instructions in README.md.
  pause
  exit /b 1
)
".venv-chatterbox\Scripts\python.exe" scripts\check_local_setup.py --verify-model
set "check_result=%errorlevel%"
pause
exit /b %check_result%
