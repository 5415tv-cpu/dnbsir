# Kill all python and uvicorn processes
Stop-Process -Name "python" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "uvicorn" -Force -ErrorAction SilentlyContinue

Write-Host "All servers killed."
Start-Sleep -Seconds 2

# Start the server
Write-Host "Starting clean server instance..."
$env:PYTHONPATH = "c:\Users\A\Desktop\AI_Store"
Start-Process -FilePath "python" -ArgumentList "-m uvicorn server.webhook_app:app --host 0.0.0.0 --port 8080 --reload" -NoNewWindow
