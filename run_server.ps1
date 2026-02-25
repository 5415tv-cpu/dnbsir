
# run_server.ps1 - Robust Server Starter
# 1. Kills process on port 8080
# 2. Starts Uvicorn
# 3. Opens browser only once

$ErrorActionPreference = "SilentlyContinue"

Write-Host "🛑 Checking port 8080..." -ForegroundColor Yellow

# 1. Kill process on port 8080
$tcp = Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue
if ($tcp) {
    $pid_to_kill = $tcp.OwningProcess
    Write-Host "killing process $pid_to_kill on port 8080..." -ForegroundColor Red
    Stop-Process -Id $pid_to_kill -Force
    Start-Sleep -Seconds 1
}

# 2. Start Server
Write-Host "🚀 Starting Server..." -ForegroundColor Green
$serverProcess = Start-Process -FilePath "python" -ArgumentList "-m uvicorn main:app --host 0.0.0.0 --port 8080 --reload" -PassThru -NoNewWindow

# 3. Wait for server to be ready (simple delay or check)
Start-Sleep -Seconds 3

# 4. Open Browser (Single Instance Check)
# We can't easily check if *our* tab is open, but we can just open it once here.
# The user's issue was likely 'Start-Process python' causing a new window which RERAN the script or main.py logic.
# By using a dedicated script, we control the browser launch.

Write-Host "🌐 Opening Browser..." -ForegroundColor Cyan
Start-Process "http://localhost:8080"

# Keep script running to monitor server (optional, or just exit)
# user needs to see output, so we don't exit immediately if run in new window.
# But if run in existing terminal, we want to see logs.
# Since we started uvicorn with -NoNewWindow, it runs in background/async if we don't wait?
# Actually Start-Process with -NoNewWindow spawns it attached to current console but asynchronous return?
# Let's try running it directly in foreground if possible, or wait-process.

Wait-Process -Id $serverProcess.Id
