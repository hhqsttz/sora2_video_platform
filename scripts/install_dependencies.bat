@echo off
cd /d "%~dp0.."

echo [INFO] Installing Dependencies...

if exist "E:\my_env\fastapi_env\Scripts\python.exe" (
    "E:\my_env\fastapi_env\Scripts\python.exe" -m pip install -r requirements.txt
) else (
    python -m pip install -r requirements.txt
)

pause