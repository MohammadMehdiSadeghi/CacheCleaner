@echo off
chcp 65001 >nul
title Cache Cleaner
cd /d "%~dp0"

rem Pick a Python that actually has pywebview installed (the default `python` on this
rem machine may be another environment, so test each candidate instead of trusting PATH).
set "PY="
for %%P in (
  "%LOCALAPPDATA%\Programs\Python\Python314\pythonw.exe"
  "%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"
  "%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
) do if not defined PY if exist %%P %%P -c "import webview" >nul 2>&1 && set "PY=%%~P"

if not defined PY for /f "delims=" %%i in ('where pythonw 2^>nul') do (
  if not defined PY %%i -c "import webview" >nul 2>&1 && set "PY=%%i"
)
if not defined PY for /f "delims=" %%i in ('where python 2^>nul') do (
  if not defined PY %%i -c "import webview" >nul 2>&1 && set "PY=%%i"
)

if defined PY (
    start "" "%PY%" "%~dp0app.py"
    exit /b 0
)

echo.
echo   Could not find a Python with pywebview installed.
echo   Install it with:  "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" -m pip install pywebview
echo.
pause
exit /b 1
