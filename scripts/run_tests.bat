@echo off
cd /d "%~dp0.."

echo [INFO] Running Comprehensive Tests...

if exist "E:\my_env\fastapi_env\Scripts\python.exe" (
    "E:\my_env\fastapi_env\Scripts\python.exe" test_api.py
) else (
    python test_api.py
)

pause