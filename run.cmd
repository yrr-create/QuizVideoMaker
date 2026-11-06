@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=python"
where py >nul 2>nul
if not errorlevel 1 set "PYTHON=py"
if exist "%LocalAppData%\Programs\Python\Python313\python.exe" set "PYTHON=%LocalAppData%\Programs\Python\Python313\python.exe"
if exist ".venv\Scripts\python.exe" goto ready
echo Preparing Python environment...
"%PYTHON%" -m venv .venv
if errorlevel 1 goto failed
:ready
if exist ".venv\quiz-dependencies-ready" goto generate
echo Installing dependencies. Internet connection required...
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
type nul > ".venv\quiz-dependencies-ready"
:generate
".venv\Scripts\python.exe" generate.py
if errorlevel 1 goto failed
echo.
echo Finished. Your MP4 is in the videos folder.
if /i "%~1"=="--no-pause" exit /b 0
pause
exit /b 0
:failed
echo.
echo Failed. Read the error above. Python 3.10+ and Internet access are required.
if /i "%~1"=="--no-pause" exit /b 1
pause
exit /b 1
