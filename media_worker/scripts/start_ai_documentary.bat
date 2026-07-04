@echo off
echo ==================================================
echo 🚀 AI Documentary Complete System Startup
echo ==================================================

echo [1/2] Starting GPU Controller (Go Worker + ComfyUI)...
start "Go Worker" cmd /k "cd C:\Users\A\Desktop\AI_Store\core_engine\go-worker && .\worker.exe"

echo [2/2] Opening Browser...
timeout /t 3 /nobreak >nul
start https://tantanfab.com/admin/dashboard

echo All systems launched!
exit
