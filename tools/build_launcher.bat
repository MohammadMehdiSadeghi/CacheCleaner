@echo off
rem Build CacheCleaner.exe (project root) from tools\launcher.cs with assets\sparkles.ico
rem embedded as the file's own icon. Uses the csc.exe that ships with Windows.
setlocal
cd /d "%~dp0.."

set "CSC=%WINDIR%\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if not exist "%CSC%" set "CSC=%WINDIR%\Microsoft.NET\Framework\v4.0.30319\csc.exe"
if not exist "%CSC%" (
    echo.
    echo   csc.exe not found. Install .NET Framework 4.x - included with Windows 10/11.
    echo.
    exit /b 1
)
if not exist "assets\sparkles.ico" (
    echo   assets\sparkles.ico missing - run: python tools\make_icon.py
    exit /b 1
)

"%CSC%" /nologo /target:winexe /platform:anycpu /optimize+ ^
    /out:CacheCleaner.exe ^
    /win32icon:assets\sparkles.ico ^
    /r:System.dll ^
    tools\launcher.cs
if errorlevel 1 (
    echo   build failed
    exit /b 1
)

echo   built CacheCleaner.exe
exit /b 0
