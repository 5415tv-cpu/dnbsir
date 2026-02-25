# deploy.ps1 - 동네비서 자동 배포 스크립트 (PowerShell)

# 한글 깨짐 방지: 콘솔 코드페이지를 UTF-8(65001)로 변경
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================" -ForegroundColor Green
Write-Host "  동네비서 자동 배포 시작 (서비스: dnbsir-api)" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

$ErrorActionPreference = "Stop"

# 설정
$PROJECT_ID = "gen-lang-client-0456120803"
$SERVICE_NAME = "dnbsir-api"
$REGION = "us-central1"
$IMAGE_NAME = "gcr.io/$PROJECT_ID/$SERVICE_NAME"

# 1. 사전 점검
Write-Host "[1/6] 사전 점검 중..." -ForegroundColor Yellow

if (-not (Test-Path "main.py")) {
    Write-Host "❌ main.py 파일을 찾을 수 없습니다!" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "Dockerfile")) {
    Write-Host "❌ Dockerfile을 찾을 수 없습니다!" -ForegroundColor Red
    exit 1
}

# 2. 로컬 테스트 (생략)
Write-Host "[2/6] 로컬 테스트 중... (생략)" -ForegroundColor Yellow

# 3. Docker 이미지 빌드 및 푸시 Strategy
Write-Host "[3/6] Container Build Strategy Check..." -ForegroundColor Yellow
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$tagName = "${IMAGE_NAME}:${timestamp}"

# Check Docker Daemon (Try-Catch wrapper for safety)
$dockerAvailable = $false
try {
    docker info | Out-Null
    if ($LASTEXITCODE -eq 0) { $dockerAvailable = $true }
}
catch {
    $dockerAvailable = $false
}

if ($dockerAvailable) {
    Write-Host "🐳 Local Docker detected. Building locally..." -ForegroundColor Green
    
    # Local Build
    docker build . -t $tagName
    if ($LASTEXITCODE -ne 0) { exit 1 }
    
    # Push to GCR
    Write-Host "[4/6] Pushing to Container Registry..." -ForegroundColor Yellow
    docker push $tagName
    if ($LASTEXITCODE -ne 0) { exit 1 }

}
else {
    Write-Host "☁️ Local Docker not found/running. Using Google Cloud Build..." -ForegroundColor Cyan
    
    # Remote Build via Cloud Build
    # Note: This requires the correct project to be set in gcloud config
    gcloud builds submit --tag $tagName .
    if ($LASTEXITCODE -ne 0) { 
        Write-Host "❌ Cloud Build Failed!" -ForegroundColor Red
        exit 1 
    }
}

# 5. Cloud Run 배포
Write-Host "[5/6] Cloud Run에 배포 중..." -ForegroundColor Yellow

# [Professional] Generate env_vars.yaml to handle special characters (commas)
$envContent = @"
APP_ENV: production
API_URL: https://dnbsir-api-ap33e42daq-uc.a.run.app
CORS_ORIGINS: "*"
WEBHOOK_TOKEN: test_token_1234
GOOGLE_API_KEY: AIzaSyDWPo6d9e2YsvHhKGs1vO-LYx1yatoFsmo
SOLAPI_API_KEY: NCSR1SXBMOH13MYO
SOLAPI_API_SECRET: S8T5X4B5PBFLDUDIAUB1ZOHLB8SIRQIY
SENDER_PHONE: 01023847447
KAKAO_REST_API_KEY: cf44d0281c879804571f2964f39c09ed
TOSS_CLIENT_KEY: test_ck_PBal2vxj81ND2OPW6a7135RQgOAN
TOSS_SECRET_KEY: test_sk_26DlbXAaV0Kbn1ljMQa43qY50Q9R
TZ: Asia/Seoul
# [CRITICAL] Cloud SQL Connection - User must fill this DSN (Commented out until provided)
# DB_BACKEND: cloudsql
# CLOUD_SQL_DSN: postgresql+pg8000://[USER]:[PASSWORD]@/[DB_NAME]?unix_sock=/cloudsql/[PROJECT_ID]:[REGION]:[INSTANCE_NAME]
"@
Set-Content "env_vars.yaml" $envContent -Encoding Ascii

# 주의: PowerShell에서는 백틱(`)으로 줄바꿈합니다.
gcloud run deploy $SERVICE_NAME `
    --image "$tagName" `
    --region $REGION `
    --platform managed `
    --allow-unauthenticated `
    --port 8080 `
    --memory 2Gi `
    --cpu 1 `
    --timeout 900 `
    --env-vars-file "env_vars.yaml" `
    --max-instances 10 `
    --min-instances 1 `
    --quiet

if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Cloud Run 배포 실패" -ForegroundColor Red
    exit 1
}

$valStatus = gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)'

Write-Host "✅ Cloud Run 배포 완료" -ForegroundColor Green
Write-Host "확인 URL: $valStatus" -ForegroundColor Cyan
