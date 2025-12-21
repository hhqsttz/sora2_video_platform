@echo off
cd /d "%~dp0.."

echo [INFO] Running Comprehensive Tests...

REM Check for specific environment first
if exist "E:\my_env\fastapi_env\Scripts\python.exe" (
    echo [INFO] Using E:\my_env\fastapi_env python...
    "E:\my_env\fastapi_env\Scripts\python.exe" test_api.py
) else (
    echo [INFO] Using system python...
    python test_api.py
)

pause