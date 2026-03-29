@echo off
echo Starting Grok Local AI Server...

start "Grok Server" cmd /c "uvicorn main:app --host 127.0.0.1 --port 8000"

timeout /t 3 /nobreak > NUL

echo Opening the web client...
start index.html