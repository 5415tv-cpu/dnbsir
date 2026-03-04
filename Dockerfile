# 1. 파이썬 3.9 버전을 기반으로 시작합니다.
FROM python:3.11-slim

# 0. 로그 즉시 출력 (Cloud Run 필수)
ENV PYTHONUNBUFFERED True

# 2. 서버 안의 작업 공간을 만듭니다.
WORKDIR /app

# 3. 필요한 도구 목록을 복사하고 설치합니다. (정확성 강조)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 사장님의 소중한 코드를 모두 복사합니다.
ENV BUILD_DATE="2026-02-16-01-force-rebuild"
COPY . .

# 5. 구글 클라우드가 요구하는 8080 포트로 비서를 대기시킵니다.
ENV PORT 8080
EXPOSE 8080

# 6. 비서를 출근시킵니다. (Gunicorn으로 안정적인 운영 - 구글 표준 권장: CPU 코어 * 2 + 1, 여기선 가볍게 2~4)
# 6. 비서를 출근시킵니다. (Gunicorn으로 안정적인 운영 - 메모리 최적화를 위해 워커 수 조정)
CMD ["sh", "-c", "gunicorn -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:${PORT} --workers 2 --threads 8 --timeout 0 --max-requests 1000 --max-requests-jitter 50 main:app"]
