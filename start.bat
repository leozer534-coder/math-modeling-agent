@echo off
setlocal enabledelayedexpansion
title MathModelAgent Launcher - Debug
color 0A
chcp 65001 >nul 2>&1

echo.
echo ========================================
echo    MathModelAgent - 启动调试模式
echo ========================================
echo.

set "PYTHONIOENCODING=utf-8"
set "PYTHONUTF8=1"
set "PROJ_DIR=%~dp0"

echo [调试] 项目路径: "%PROJ_DIR%"
echo.

echo [调试] 按任意键开始第1步: 启动 Redis...
pause

echo [1/4] 启动 Redis...
if exist "%PROJ_DIR%redis-temp\redis-server.exe" (
    echo [调试] 找到 Redis，准备启动...
    pushd "%PROJ_DIR%redis-temp"
    start /min "Redis" redis-server.exe redis.windows.conf
    popd
    echo [OK] Redis 已启动
) else (
    echo [跳过] 未找到内置 Redis
)
timeout /t 2 /nobreak >nul

echo.
echo [调试] 按任意键开始第2步: 准备后端...
pause

echo [2/4] 准备后端...
pushd "%PROJ_DIR%backend"
echo [调试] 当前目录: %CD%

if not exist ".venv" (
    echo 首次运行，创建虚拟环境...
    uv venv
    if errorlevel 1 (
        echo [错误] uv venv 失败！请确认 uv 已安装
        pause
        exit /b 1
    )
)

uv sync --quiet 2>nul
echo [OK] 后端就绪
popd

echo.
echo [调试] 按任意键开始第3步: 启动后端...
pause

echo [3/4] 启动后端服务...
pushd "%PROJ_DIR%backend"
start /min "Backend - MathModelAgent" cmd /k "chcp 65001 >nul & set PYTHONIOENCODING=utf-8 & set PYTHONUTF8=1 & set ENV=DEV & .venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
popd
echo [OK] 后端启动中 (http://localhost:8000)

echo 等待后端就绪...
timeout /t 5 /nobreak >nul

echo.
echo [调试] 按任意键开始第4步: 启动前端...
pause

echo [4/4] 启动前端服务...
pushd "%PROJ_DIR%frontend"
echo [调试] 当前目录: %CD%

if not exist "node_modules" (
    echo 首次运行，安装前端依赖...
    call pnpm install
    if errorlevel 1 (
        echo [错误] pnpm install 失败！
        pause
        exit /b 1
    )
)

start /min "Frontend - MathModelAgent" cmd /k "chcp 65001 >nul & npx vite"
popd
echo [OK] 前端启动中 (http://localhost:5173)

echo 等待前端就绪...
timeout /t 5 /nobreak >nul

echo.
echo ========================================
echo   所有服务已启动！
echo ========================================
echo.
echo   前端: http://localhost:5173
echo   后端: http://localhost:8000
echo   API:  http://localhost:8000/docs
echo.

start "" "http://localhost:5173"

echo.
echo   服务在后台运行中，可关闭此窗口。
echo   停止所有服务请运行 stop.bat
echo.
echo 按任意键关闭此窗口（服务保持运行）...
pause >nul
