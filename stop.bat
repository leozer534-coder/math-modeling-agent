@echo off
chcp 65001 >nul
color 0C
cls

echo.
echo ========================================
echo    停止 MathModelAgent 服务
echo ========================================
echo.

echo 正在关闭所有服务...
echo.

REM 关闭 Redis 进程
taskkill /F /IM redis-server.exe /T >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Redis 服务已停止
) else (
    echo [信息] Redis 服务未运行
)

REM 关闭后端进程 (uvicorn)
taskkill /F /FI "WINDOWTITLE eq MathModelAgent Backend*" >nul 2>&1
taskkill /F /IM uvicorn.exe /T >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] 后端服务已停止
) else (
    echo [信息] 后端服务未运行
)

REM 关闭前端进程 (node/vite)
taskkill /F /FI "WINDOWTITLE eq MathModelAgent Frontend*" >nul 2>&1
taskkill /F /IM node.exe /T >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] 前端服务已停止
) else (
    echo [信息] 前端服务未运行
)

echo.
echo ========================================
echo 所有服务已停止
echo ========================================
echo.
pause
