@echo off
cd /d "%~dp0.."

echo [INFO] Starting Sora2 Video Platform...
echo [INFO] API Docs: http://localhost:8000/docs
echo [INFO] Frontend: http://localhost:8000/
echo.

start http://localhost:8000/

REM Check for specific environment first
if exist "E:\my_env\fastapi_env\Scripts\python.exe" (
    echo [INFO] Using E:\my_env\fastapi_env python...
    "E:\my_env\fastapi_env\Scripts\python.exe" -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
) else (
    echo [INFO] Using system python...
    python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
)