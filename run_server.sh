#!/bin/bash
# run_server.sh
# PM2-style infinite loop watchdog

echo "🚀 [Watchdog] Starting AI Store API Server Guardian..."

# Kill any existing stray processes
pkill -f "python.*uvicorn" || true

while true; do
  echo "✅ [Watchdog] Spawning new uvicorn process..."
  python -m uvicorn app:app --host 0.0.0.0 --port 8000
  
  # If we reach here, uvicorn crashed or was stopped
  EXIT_CODE=$?
  echo "⚠️ [Watchdog] Uvicorn crashed or stopped with code $EXIT_CODE."
  echo "⚠️ [Watchdog] Restarting in 3 seconds to ensure 100% uptime..."
  sleep 3
done
