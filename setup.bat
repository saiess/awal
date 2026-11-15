@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3.12 scripts\setup_local.py
) else (
  where python >nul 2>nul
  if errorlevel 1 (
    echo Install 64-bit Python 3.12 and Git for Windows, then run setup.bat again.
    echo See README.md for instructions.
    pause
    exit /b 1
  )
  python scripts\setup_local.py
)
set "setup_result=%errorlevel%"
if not "%setup_result%"=="0" echo Setup did not complete. Fix the reported issue and run setup.bat again.
pause
exit /b %setup_result%
