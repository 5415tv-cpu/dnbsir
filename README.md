# 동네비서

똑똑한 AI 이웃 - 소상공인을 위한 스마트 매장 관리 시스템

## 기능

- **매장 예약/주문**: 식당, 카페, 미용실 등 다양한 매장 예약
- **택배 접수**: 로젠택배 연동 간편 접수
- **AI 24시간 응대**: 자동 주문/예약 접수
- **단골 고객 관리**: AI가 고객 취향 기억

## 배포

### Streamlit Cloud

1. GitHub에 저장소 생성
2. Streamlit Cloud에서 저장소 연결
3. Secrets 설정 (secrets_template.toml 참고)
4. 배포 완료

### Secrets 설정

Streamlit Cloud > App Settings > Secrets에 다음 입력:

```toml
ADMIN_PASSWORD = "your_password"
GOOGLE_API_KEY = "your_gemini_api_key"
SOLAPI_API_KEY = "your_solapi_key"
SOLAPI_API_SECRET = "your_solapi_secret"
SENDER_PHONE = "01012345678"
spreadsheet_url = "https://docs.google.com/spreadsheets/d/YOUR_ID/edit"

[gcp_service_account]
type = "service_account"
project_id = "your-project"
# ... (service_account.json 내용)
```

## 커스텀 도메인 설정

1. Streamlit Cloud 배포 완료 후
2. App Settings > Custom domain
3. `dnbsir.com` 입력
4. DNS 설정:
   - CNAME: `@` → `your-app.streamlit.app`
   - 또는 A 레코드: Streamlit 제공 IP

## 사용요금

| 구분 | 월 요금 |
|------|---------|
| 일반/간이 사업자 | 50,000원 (부가세 별도) |
| 택배사업자 | 30,000원 (부가세 별도) |
| 농어민 | 30,000원 (부가세 포함) |
| 기업고객 | 상담요망 |

## 기술 스택

- Streamlit
- Google Gemini AI
- Google Sheets (DB)
- Solapi SMS

