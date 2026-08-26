@echo off
REM HoopMind launcher: Flask backend + Streamlit UI
set PYTHONUTF8=1
cd /d "%~dp0"
REM Optional local package dir (dev machine only); ignored elsewhere.
if exist "%USERPROFILE%\hmdeps" set PYTHONPATH=%USERPROFILE%\hmdeps

start "HoopMind API" cmd /k python -X utf8 webhook.py
timeout /t 3 /nobreak >nul
start "HoopMind UI"  cmd /k python -X utf8 -m streamlit run streamlit_app.py

echo.
echo  API   : http://localhost:5000
echo  UI    : http://localhost:8501
echo  Close the two windows to stop.
