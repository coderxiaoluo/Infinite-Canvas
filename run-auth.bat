@echo off
cd /d "%~dp0"

set "PYEXE=%~dp0python\python.exe"
if not exist "%PYEXE%" set "PYEXE=python"

echo Stopping previous server on port 3000 (if any)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":3000" ^| findstr "LISTENING"') do (
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul

rem 启用登录模式（需先 docker compose -f docker-compose.auth.yml up -d 并执行 alembic upgrade head）
set "AUTH_MODE=required"
set "DATABASE_URL=postgresql+asyncpg://infinite_canvas:infinite_canvas@127.0.0.1:5433/infinite_canvas"
set "JWT_SECRET=change-me-to-a-long-random-string"

echo Starting Infinite Canvas (AUTH_MODE=required)...
echo Visit: http://127.0.0.1:3000/
echo Login:  http://127.0.0.1:3000/login
echo Admin:  http://127.0.0.1:3000/members
echo Auth status: http://127.0.0.1:3000/api/auth/status
echo Press Ctrl+C to stop.
echo.

"%PYEXE%" main.py

echo.
echo Server stopped.
pause
