
# 1. Port 8080 Cleanup (Force Kill)
$port = 8080
Write-Host "🔍 Port $port 점유 확인 중..."

$process = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
if ($process) {
    $pid_val = $process.OwningProcess
    Write-Host "⚠️ Port $port 사용 중 (PID: $pid_val). 강제 종료합니다."
    Stop-Process -Id $pid_val -Force
    Start-Sleep -Seconds 1
}
else {
    Write-Host "✅ Port $port 사용 가능."
}

# 2. Start Backend Server (Background)
Write-Host "🚀 서버 시작 중 (main.py)..."
$serverProcess = Start-Process -FilePath "python" -ArgumentList "main.py" -PassThru -NoNewWindow

# 3. Health Check & Browser Open (Once)
$url = "http://localhost:8080"
$maxRetries = 30
$retryCount = 0
$serverReady = $false

Write-Host "⏳ 서버 준비 대기 중..."

while ($retryCount -lt $maxRetries) {
    try {
        $response = Invoke-WebRequest -Uri "$url/health" -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            $serverReady = $true
            break
        }
    }
    catch {
        Start-Sleep -Milliseconds 500
        $retryCount++
        Write-Host "." -NoNewline
    }
}

Write-Host ""

if ($serverReady) {
    Write-Host "✅ 서버 준비 완료! 브라우저를 실행합니다."
    Start-Process "$url/admin"
}
else {
    Write-Host "❌ 서버 시작 실패. 로그를 확인해주세요."
    Stop-Process -Id $serverProcess.Id -Force
}
