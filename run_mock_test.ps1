$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING="utf-8"

Write-Host "1. Redis 서버(우체국) 시작..."
Start-Process -FilePath ".\Redis\redis-server.exe" -WindowStyle Hidden
Start-Sleep -Seconds 1

Write-Host "2. Mock ComfyUI 서버 시작 (포트 8188)..."
Start-Process -FilePath "python.exe" -ArgumentList "mock_comfyui.py" -RedirectStandardOutput "mock_comfyui.log" -RedirectStandardError "mock_comfyui_err.log" -WindowStyle Hidden
Start-Sleep -Seconds 2

Write-Host "3. Celery 워커 시작..."
Start-Process -FilePath ".\venv_worker\Scripts\celery.exe" -ArgumentList "-A worker worker --pool=solo --loglevel=info" -RedirectStandardOutput "worker.log" -RedirectStandardError "worker_err.log" -WindowStyle Hidden
Start-Sleep -Seconds 3

Write-Host "=========================================================="
Write-Host "🚀 모든 인프라가 가동되었습니다. 테스트 시뮬레이터를 실행합니다!"
Write-Host "=========================================================="

$env:PYTHONIOENCODING="utf-8"
& ".\venv_worker\Scripts\python.exe" test_queue.py

Write-Host "테스트가 완료되었습니다! 생성된 영상 결과물을 확인해 보세요."
Write-Host "(C:\ComfyUI\output 경로에 파일이 생성되었을 것입니다.)"

# 테스트 종료 후 모두 정리
Stop-Process -Name "redis-server" -ErrorAction SilentlyContinue
Stop-Process -Name "celery" -ErrorAction SilentlyContinue
Stop-Process -Name "python" -ErrorAction SilentlyContinue
