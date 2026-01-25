# 🚀 동네비서(dnbsir.com) 배포 가이드

코드 업데이트가 GitHub에 완료되었습니다!
이제 Streamlit Cloud에 연결하고 도메인을 설정하기만 하면 됩니다.

## 1단계: Streamlit Cloud 앱 생성
1. [share.streamlit.io](https://share.streamlit.io/) 접속 및 로그인.
2. 오른쪽 상단 **[New app]** 버튼 클릭.
3. **Use existing repo** 선택.
4. 설정값 입력:
   - **Repository**: `5415tv-cpu/dnbsir`
   - **Branch**: `main`
   - **Main file path**: `main.py`
5. **[Deploy!]** 버튼 클릭.

## 2단계: Secrets(비밀키) 설정 (필수!)
앱이 실행되려다가 에러가 날 수 있습니다. DB 비밀번호 등 보안 키를 클라우드에 알려줘야 합니다.

1. 배포 중인 앱 우측 하단 **[Manage app]** 클릭 (또는 대시보드에서 앱 옆의 `...` > Settings).
2. **Secrets** 탭 클릭.
3. 아래 내용을 복사해서 붙여넣고 **[Save]** 하세요.

```toml
# 앱 접속 주소
APP_URL = "https://dnbsir.com"
ADMIN_PASSWORD = "1234"

# Naver OCR (할당받은 키 입력)
naver_ocr_url = ""
naver_ocr_secret = ""

# 기타 API 키 (필요시 채워넣으세요)
GOOGLE_API_KEY = "" 
```

## 3단계: 도메인 연결 (dnbsir.com)
1. 앱 대시보드에서 앱 옆의 `...` 클릭 > **Settings**.
2. **General** 탭 > **Custom domain** 섹션.
3. `dnbsir.com` 입력 후 엔터.
4. 화면에 **"Please set up a CNAME record..."** 라는 안내가 뜹니다.
5. 보여주는 `Target` 주소(예: `ingress.streamlit.io` 등)를 복사하세요.

## 4단계: DNS 설정 (도메인 구입처)
1. 가비아, 후이즈, GoDaddy 등 도메인을 산 사이트에 접속.
2. **DNS 관리(DNS 설정)** 메뉴로 이동.
3. **레코드 추가**:
   - **타입**: `CNAME`
   - **호스트(이름)**: `www` (또는 `@` 루트 도메인 지원 여부 확인)
   - **값(타겟)**: 아까 복사한 Streamlit Target 주소.
   - **TTL**: 3600 (기본값)
4. 저장 후 약 30분~1시간 기다리면 연결됩니다!

---
**주의사항**
- **데이터 초기화**: 무료 클라우드(Community Cloud)는 앱이 절전 모드에 들어가거나 재부팅되면 **SQLite 데이터(회원가입 정보)가 초기화**될 수 있습니다. 
- 영구 저장이 필요하면 Google Sheets 모드를 다시 활성화하거나 별도의 호스팅 DB가 필요합니다.
