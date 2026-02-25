# 🎨 동네비서 프로젝트 - AI 코딩 어시스턴트 가이드

> **목적**: Cursor와 같은 AI 코딩 도구가 프로젝트의 디자인 일관성을 유지하도록 강제하는 규칙 문서
> **대상**: 60대 개발자님의 동네비서 앱 (FastAPI + Jinja2 템플릿)
> **버전**: v1.0.0
> **최종 수정**: 2026-02-10

---

## 📋 목차
1. [프로젝트 개요](#프로젝트-개요)
2. [핵심 디자인 철학](#핵심-디자인-철학)
3. [디자인 시스템 (색상/폰트/간격)](#디자인-시스템)
4. [컴포넌트 규칙](#컴포넌트-규칙)
5. [금지 사항](#금지-사항)
6. [파일 구조 규칙](#파일-구조-규칙)
7. [코드 작성 원칙](#코드-작성-원칙)

---

## 🎯 프로젝트 개요

**프로젝트명**: 동네비서 (AI Store)  
**기술 스택**: Python 3.9+ / FastAPI / Jinja2 / SQLite (→ PostgreSQL 마이그레이션 예정)  
**배포 환경**: Google Cloud Run (미국 서버 `us-central1`)  
**대상 사용자**: 60대 사장님, 농민, 택배 기사  
**디자인 컨셉**: 뉴브루탈리즘 (Neo-Brutalism) - 굵은 테두리, 그림자, 강렬한 대비

---

## 🎨 핵심 디자인 철학

### 1. **일관성 우선**
- 모든 페이지는 `base.html`을 상속받아야 합니다.
- CSS는 **인라인 스타일** 또는 `/static/css/style.css` 만 사용합니다.
- **절대 새로운 CSS 파일을 만들지 마세요.**

### 2. **뉴브루탈리즘 스타일 유지**
- 모든 카드/버튼은 **3~4px 굵은 검정 테두리** (`border: 3px solid #1A1A1A`)
- 그림자는 **단단한 박스 섀도우** (`box-shadow: 4px 4px 0px #ccc` 또는 `#555`)
- 둥근 모서리는 **최소화** (`border-radius: 5px` 이하)

### 3. **모바일 퍼스트**
- 모든 UI는 **360px 너비**에서 먼저 테스트합니다.
- `viewport` 메타 태그는 절대 수정하지 마세요:
  ```html
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
  ```

---

## 🎨 디자인 시스템

### 색상 팔레트 (변경 금지)
```css
:root {
    --bg-color: #E0E0E0;        /* 배경: 옅은 회색 */
    --text-color: #1A1A1A;      /* 텍스트: 거의 검정 */
    --point-color: #FFFFFF;     /* 카드 배경: 순백색 */
    --accent-green: #27AE60;    /* 농가 관련 기능 */
    --accent-shadow: #CCCCCC;   /* 기본 그림자 */
    --dark-shadow: #555555;     /* 어두운 그림자 */
}
```

**사용 예시**:
- **일반 카드**: `background: #fff; border: 3px solid #1A1A1A; box-shadow: 4px 4px 0px #ccc;`
- **강조 버튼**: `background: #1A1A1A; color: #fff; box-shadow: 4px 4px 0px #555;`
- **농가 버튼**: `background: #27AE60; color: #fff; border: 3px solid #1A1A1A;`

---

### 타이포그래피 (변경 금지)
```css
body {
    font-family: 'Pretendard', -apple-system, sans-serif;
    font-weight: 800; /* 기본 굵기 */
}

h1 {
    font-size: 1.8rem;
    font-weight: 900;
    letter-spacing: -1px;
}

/* 카드 타이틀 */
.card-title {
    font-size: 2.2rem;
    font-weight: 900;
    letter-spacing: -1px;
}

/* 버튼 텍스트 */
.main-btn {
    font-weight: 900;
    font-size: 1.1rem;
}
```

---

### 간격 시스템 (8px 기준)
```css
/* 기본 간격 */
--spacing-xs: 5px;
--spacing-sm: 10px;
--spacing-md: 15px;
--spacing-lg: 20px;
--spacing-xl: 25px;
```

**적용 규칙**:
- 카드 간격: `margin-bottom: 20px;`
- 카드 내부 여백: `padding: 20px;`
- 그리드 갭: `gap: 15px;`

---

## 🧩 컴포넌트 규칙

### 1. 카드 컴포넌트
```html
<!-- 기본 카드 (흰색 배경) -->
<div style="border: 3px solid #1A1A1A; background: #fff; padding: 20px; margin-bottom: 20px; box-shadow: 4px 4px 0px #ccc;">
    <div style="font-size: 0.95rem; font-weight: 800; color: #555; margin-bottom: 5px;">라벨</div>
    <div style="font-size: 2.2rem; font-weight: 900; color: #1A1A1A; letter-spacing: -1px;">
        메인 텍스트
    </div>
</div>

<!-- 강조 카드 (검은 배경) -->
<div style="border: 3px solid #1A1A1A; background: #1A1A1A; color: #fff; padding: 20px; margin-bottom: 20px; box-shadow: 4px 4px 0px #555;">
    컨텐츠
</div>
```

---

### 2. 버튼 컴포넌트
```html
<!-- 기본 버튼 (검은 배경) -->
<button class="main-btn" style="background: #1A1A1A; color: white; padding: 18px; border-radius: 5px; font-weight: 900; width: 100%; border: none; cursor: pointer;">
    클릭하기
</button>

<!-- 농가 전용 버튼 (녹색) -->
<a href="/admin/farm/orders" style="text-decoration: none; color: inherit;">
    <div style="border: 3px solid #1A1A1A; background: #27ae60; color: #fff; padding: 15px; text-align: center; font-weight: 900; box-shadow: 3px 3px 0px #1e8449;">
        🚜 농가 주문
    </div>
</a>
```

---

### 3. 그리드 레이아웃
```html
<!-- 2열 그리드 (균등 분할) -->
<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
    <div>첫 번째</div>
    <div>두 번째</div>
</div>
```

---

### 4. 하단 네비게이션 (수정 금지)
```html
<nav style="position: fixed; bottom: 0; width: 100%; background: #fff; border-top: 4px solid #1A1A1A; display: flex; justify-content: space-around; padding: 10px 0; z-index: 100;">
    <a href="/admin/dashboard" style="text-decoration: none; color: #1a1a1a; text-align: center;">
        <div style="font-size: 1.2rem;">🏠</div>
        <div style="font-weight: 900; font-size: 0.8rem;">홈</div>
    </a>
    <a href="/market" style="text-decoration: none; color: #1a1a1a; text-align: center;">
        <div style="font-size: 1.2rem;">🛒</div>
        <div style="font-weight: 900; font-size: 0.8rem;">마켓</div>
    </a>
    <a href="/admin/farm/orders" style="text-decoration: none; color: #1a1a1a; text-align: center;">
        <div style="font-size: 1.2rem;">📅</div>
        <div style="font-weight: 900; font-size: 0.8rem;">예약</div>
    </a>
    <a href="/admin/tax" style="text-decoration: none; color: #1a1a1a; text-align: center;">
        <div style="font-size: 1.2rem;">📒</div>
        <div style="font-weight: 900; font-size: 0.8rem;">장부</div>
    </a>
</nav>
```

---

## ❌ 금지 사항

### 절대 하지 말아야 할 것들:
1. ❌ **Tailwind CSS, Bootstrap 등 외부 CSS 프레임워크 추가**
2. ❌ **새로운 CSS 파일 생성** (`style.css` 외 금지)
3. ❌ **색상 변경** (위에서 정의한 색상 팔레트만 사용)
4. ❌ **둥근 모서리 과다 사용** (`border-radius` 5px 초과 금지)
5. ❌ **그라디언트, 애니메이션 과다 사용** (뉴브루탈리즘에 어긋남)
6. ❌ **폰트 변경** (Pretendard, -apple-system만 사용)
7. ❌ **base.html 구조 변경** (상속 구조 유지)
8. ❌ **하단 네비게이션 위치/스타일 변경**

---

## 📁 파일 구조 규칙

### 템플릿 파일 생성 시:
```
templates/
├── base.html           (✅ 절대 수정 금지 - 모든 페이지의 기본 틀)
├── dashboard.html      (✅ 대시보드 페이지)
├── login.html          (✅ 로그인 페이지)
├── market.html         (✅ 마켓 페이지)
└── [새로운_페이지].html (⚠️ 반드시 base.html 상속)
```

**새 템플릿 작성 예시**:
```html
{% extends "base.html" %}

{% block current_menu %}현재 메뉴명{% endblock %}
{% block menu_title %}페이지 타이틀{% endblock %}

{% block content %}
<!-- 여기에 페이지 내용 작성 -->
<div style="border: 3px solid #1A1A1A; background: #fff; padding: 20px; margin-bottom: 20px; box-shadow: 4px 4px 0px #ccc;">
    컨텐츠
</div>
{% endblock %}
```

---

## 💻 코드 작성 원칙

### FastAPI 라우트 작성 시:
```python
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")

@app.get("/새경로", response_class=HTMLResponse)
async def new_page(request: Request):
    # 1. 세션 검증
    store_id = request.cookies.get("admin_session")
    if not store_id:
        return RedirectResponse(url="/admin")
    
    # 2. 데이터 조회
    data = db.get_something(store_id)
    
    # 3. 템플릿 렌더링
    return templates.TemplateResponse("new_page.html", {
        "request": request,
        "data": data
    })
```

---

### 데이터베이스 접근 시:
```python
# ✅ 올바른 방법: db_manager 모듈 사용
import db_manager as db

store = db.get_store(store_id)
stats = db.get_today_stats(store_id)

# ❌ 잘못된 방법: 직접 SQL 작성
# conn = sqlite3.connect("database.db")
# cursor = conn.execute("SELECT * FROM stores WHERE id=?", (store_id,))
```

---

## 🔧 AI 어시스턴트 사용 가이드

### Cursor에게 요청할 때:
**✅ 올바른 요청**:
- "dashboard.html을 참고해서 새로운 페이지를 만들어줘"
- "base.html 스타일을 유지하면서 버튼 추가해줘"
- "동일한 카드 스타일로 통계 화면 만들어줘"

**❌ 잘못된 요청**:
- "Bootstrap으로 예쁘게 만들어줘" → 금지!
- "모던한 느낌으로 디자인 바꿔줘" → 금지!
- "그라디언트 배경 추가해줘" → 금지!

---

### AI에게 전달할 컨텍스트:
```
이 프로젝트는 뉴브루탈리즘 디자인을 사용합니다.
- 굵은 검정 테두리 (3px solid #1A1A1A)
- 박스 그림자 (4px 4px 0px)
- 흰색/회색/검정 색상만 사용
- base.html을 상속받아야 함
- 인라인 스타일 사용
```

---

## 📝 체크리스트

### 새 페이지 추가 전:
- [ ] `base.html`을 `{% extends "base.html" %}`로 상속했는가?
- [ ] 카드 스타일이 `border: 3px solid #1A1A1A`인가?
- [ ] 그림자가 `box-shadow: 4px 4px 0px #ccc`인가?
- [ ] 색상이 `#E0E0E0`, `#1A1A1A`, `#FFFFFF` 중 하나인가?
- [ ] 폰트가 `Pretendard` 또는 `-apple-system`인가?
- [ ] 새로운 CSS 파일을 만들지 않았는가?

### 코드 수정 전:
- [ ] `db_manager` 모듈을 통해 DB에 접근하는가?
- [ ] 세션 검증 로직이 포함되어 있는가?
- [ ] 에러 처리가 추가되어 있는가?

---

## 🎓 학습 자료

### 참고할 파일:
1. **디자인 기준**: `templates/base.html`, `templates/dashboard.html`
2. **색상 팔레트**: `static/css/style.css`
3. **라우팅 예시**: `server/webhook_app.py`

### 추가 학습:
- **뉴브루탈리즘 디자인**: https://brutalistwebsites.com
- **FastAPI 공식 문서**: https://fastapi.tiangolo.com
- **Jinja2 템플릿**: https://jinja.palletsprojects.com

---

## 🚀 배포 전 최종 확인

### 디자인 일관성 검증:
```bash
# 모든 템플릿이 base.html을 상속받는지 확인
grep -r "extends \"base.html\"" templates/

# 금지된 CSS 프레임워크가 없는지 확인
grep -r "bootstrap\|tailwind" templates/
```

---

## 📞 문의 및 수정 요청

이 가이드에 대한 수정이 필요하면:
1. `CLAUDE.md` 파일을 직접 수정하세요.
2. 변경 사항을 팀원과 공유하세요.
3. AI 어시스턴트에게 이 문서를 다시 읽도록 지시하세요.

---

**마지막 업데이트**: 2026-02-10  
**작성자**: 동네비서 개발팀  
**버전**: v1.0.0
