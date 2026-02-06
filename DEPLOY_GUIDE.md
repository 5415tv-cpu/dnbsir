# 🚚 동네비서 프로젝트 배포 가이드 (v1.2.0)

본 문서는 강원도 태백 현장 업무를 지원하는 AI 에이전트 '동네비서'의 정석 배포 절차를 정의합니다.
미국 서버 배포 가이드 및 로컬 테스트 완료
## 1. 인프라 환경
* **운영 서버**: Google Cloud Run
* **서버 위치(Region)**: `us-central1` (미국 아이오와)
* **로컬 테스트**: `http://127.0.0.1:8080` (확인 완료)

## 2. 배포 전 체크리스트 (정확성 검증)
* [x] 메인 앱 실행 포트: `8080` 설정 확인
* [x] `Dockerfile`: 구글 클라우드용 빌드 파일 존재 확인
* [x] `requirements.txt`: 필수 라이브러리(fastapi, uvicorn 등) 포함 확인
* [x] Streamlit Cloud 관련 설정 제거 완료

## 3. 배포 절차 (GitHub -> Google Cloud)
1. 로컬에서 코드 수정 및 테스트 완료 (`Application startup complete` 확인)
2. GitHub 저장소에 `push` 실행
3. Google Cloud Console에서 자동으로 빌드 및 배포 트리거 작동
4. 최종 접속 주소: `https://api.dnbsir.com/docs`

## 4. 주의사항
* 서버가 미국에 있으므로 한국 시간대 설정(`TZ=Asia/Seoul`)을 환경 변수에 추가할 것.
* 모든 보안 키는 Google Cloud '보안 비밀 관리자'를 통해 관리할 것.
