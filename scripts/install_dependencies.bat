@echo off
cd /d "%~dp0.."

echo [INFO] Installing Dependencies...

REM Check for specific environment first
if exist "E:\my_env\fastapi_env\Scripts\python.exe" (
    echo [INFO] Using E:\my_env\fastapi_env python...
    "E:\my_env\fastapi_env\Scripts\python.exe" -m pip install -r requirements.txt
) else (
    echo [INFO] Using system python...
    python -m pip install -r requirements.txt
)

pause