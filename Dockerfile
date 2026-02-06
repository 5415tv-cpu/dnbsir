# 1. 파이썬 3.9 버전을 기반으로 시작합니다.
FROM python:3.9-slim

# 2. 서버 안의 작업 공간을 만듭니다.
WORKDIR /app

# 3. 필요한 도구 목록을 복사하고 설치합니다. (정확성 강조)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 사장님의 소중한 코드를 모두 복사합니다.
COPY . .

# 5. 구글 클라우드가 요구하는 8080 포트로 비서를 대기시킵니다.
ENV PORT 8080
EXPOSE 8080

# 6. 비서를 출근시킵니다. (uvicorn으로 실행하는 것이 정석입니다)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
