"""
숏폼 영상 생성 키오스크 API 라우터
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
POST  /api/kiosk/video/generate   → 작업 시작
GET   /api/kiosk/video/status/{id} → 진행 상태 폴링
GET   /api/kiosk/video/download/{id} → 완성 영상 다운로드
GET   /tantan                     → 탄탄제작소 키오스크 HTML 서빙
"""
from __future__ import annotations
import os, uuid, shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import ValidationError

from media_worker.schemas import AssetsSchema, MerchantFactsSchema

router = APIRouter(tags=["shortform-kiosk"])

# 업로드 이미지 임시 저장소
UPLOAD_DIR = Path(__file__).parent.parent / "static" / "kiosk_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 기본 배경 이미지 (상인이 업로드 안 했을 때 폴백)
_ASSETS_DIR = Path(__file__).parent.parent / "static" / "kiosk_assets"
DEFAULT_IMAGES = [
    str(_ASSETS_DIR / f"default_{i}.jpg")
    for i in range(1, 4)
]

# 출력 영상 디렉터리 — video_renderer와 동일한 env 변수 사용
OUTPUT_DIR = Path(
    os.environ.get(
        "SHORTFORM_OUTPUT_DIR",
        str(Path(__file__).parent.parent / "static" / "output"),
    )
)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ── 키오스크 HTML 페이지 ────────────────────────────────────────
@router.get("/tantan", response_class=HTMLResponse, include_in_schema=False)
async def shortform_kiosk_page():
    """탄탄제작소 — 상인용 숫폼 영상 제작 키오스크 UI"""
    html_path = Path(__file__).parent.parent / "static" / "shortform_kiosk.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>shortform_kiosk.html 파일을 찾을 수 없습니다</h1>", status_code=404)


# ── 영상 생성 시작 ──────────────────────────────────────────────
@router.post("/api/kiosk/video/generate")
async def start_video_generation(
    product:  str = Form(..., description="상품명 (예: 강원도 태백 고랭지 배추)"),
    price:    str = Form(..., description="가격 (예: 3kg 9,900원 배송비 포함)"),
    features: str = Form(..., description="핵심 특징 (쉼표 구분, 예: 당일 새벽 수확,산지직송)"),
    origin:   str = Form("", description="원산지 (선택)"),
    cta:      str = Form("동네비서 앱에서 주문하세요", description="행동 유도 문구"),
    bgm:      int = Form(1, description="BGM 번호 1=신뢰 2=활기 3=차분"),
    voice:    str = Form("Kore", description="Gemini TTS 음성"),
    images:   list[UploadFile] = File(default=[]),
):
    """
    상인이 입력한 팩트 JSON → Celery 워커 큐 투입.
    중복 실행 방어: 각 요청마다 유일한 job_id 발급.
    """
    # ── 팩트 유효성 검사 (백엔드 2차 방어) ──
    missing = [f for f, v in [("상품명", product), ("가격", price), ("핵심특징", features)] if not v.strip()]
    if missing:
        return JSONResponse(
            status_code=422,
            content={"error": f"필수 입력 누락: {', '.join(missing)}"}
        )

    job_id = f"kiosk-{uuid.uuid4().hex[:10]}"

    # ── 이미지 저장 ───────────────────────────
    saved_images: list[str] = []
    for img in images[:3]:                  # 최대 3장
        if img and img.filename:
            ext  = Path(img.filename).suffix.lower() or ".jpg"
            dest = UPLOAD_DIR / f"{job_id}_{len(saved_images)}{ext}"
            with open(dest, "wb") as f:
                f.write(await img.read())
            saved_images.append(str(dest))

    # 이미지 없으면 기본 배경 사용
    bg_images = saved_images if saved_images else _default_images()

    # ── [원칙1] Pydantic 스키마 검증 (프론트 1차 방어) ──────────
    try:
        facts_model = MerchantFactsSchema(
            product  = product,
            price    = price,
            features = features,
            origin   = origin or None,
            cta      = cta,
        )
        assets_model = AssetsSchema(
            bg_images    = bg_images,
            bgm_preset   = bgm,
            gemini_voice = voice,
        )
    except ValidationError as exc:
        errors = [{"field": e["loc"][-1], "msg": e["msg"]} for e in exc.errors()]
        return JSONResponse(
            status_code=422,
            content={"error": "입력 데이터 오류", "detail": errors},
        )

    merchant_facts = facts_model.model_dump()
    assets         = assets_model.model_dump()

    # ── 배치 큐 등록 (즉시 렌더링 → 심야 배치 처리) ──────────────
    # KST 00:00~07:00 야간 배치 윈도우에서 순차 처리됩니다.
    # is_test=True인 경우에만 즉시 Celery enqueue (헬스체크 테스트용).
    phone = assets.get("phone", "")   # 세션에서 전달된 전화번호

    if assets.get("is_test"):
        # ── 테스트 렌더링: 즉시 Celery enqueue ───────────────────
        try:
            from media_worker.tasks.video_tasks import generate_premium_shortform
            task = generate_premium_shortform.apply_async(
                args=[job_id, merchant_facts, assets],
                task_id=job_id,
                queue="video_tasks",
            )
            return JSONResponse({
                "task_id": task.id, "job_id": job_id,
                "status": "PENDING", "is_test": True,
                "message": "테스트 렌더링 대기 중... (크레딧 차감 없음)",
            })
        except Exception as e:
            return JSONResponse(status_code=503, content={
                "error": f"GPU 워커 연결 실패: {e}"})

    # ── 실제 주문: 배치 큐 등록 ──────────────────────────────────
    try:
        from routers.batch_scheduler import register_pending_order, _send_admin_sms
        order = register_pending_order(
            job_id=job_id,
            phone=phone,
            merchant_facts=merchant_facts,
            assets=assets,
        )

        # 고객 SMS — "7일 이내 완성" 안내
        if phone:
            try:
                from routers.tantan_payment import _send_sms
                _send_sms(
                    phone,
                    f"[동네비서] 주문이 정상 접수되었습니다! 🎬\n"
                    f"AI 홍보 영상은 약 7일 이내에 완성됩니다.\n"
                    f"완성 즉시 이 번호로 다운로드 링크를 보내드립니다."
                )
            except Exception as sms_err:
                import logging
                logging.getLogger("tantan").warning(f"접수 SMS 실패: {sms_err}")

        return JSONResponse({
            "task_id":  job_id,
            "job_id":   job_id,
            "status":   "PENDING_BATCH",
            "message":  "주문이 접수되었습니다. 약 7일 이내 완성 후 SMS로 안내드립니다.",
            "eta_days": 7,
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "error": f"주문 등록 실패: {e}"})


# ── 진행 상태 폴링 ──────────────────────────────────────────────
@router.get("/api/kiosk/video/status/{task_id}")
async def get_task_status(task_id: str):
    """
    Celery 태스크 진행 상태 반환.
    프론트엔드가 2초마다 폴링하여 로딩 오버레이를 업데이트.
    """
    from celery.result import AsyncResult
    from media_worker.celery_app import app as celery_app

    try:
        result = AsyncResult(task_id, app=celery_app)
        state  = result.state          # PENDING | PROGRESS | SUCCESS | FAILURE

        if state == "PENDING":
            return JSONResponse({
                "state":   "PENDING",
                "percent": 5,
                "message": "⏳ 영상 생성 대기 중...",
            })

        if state == "PROGRESS":
            meta = result.info or {}
            return JSONResponse({
                "state":   "PROGRESS",
                "step":    meta.get("step", 0),
                "total":   meta.get("total", 4),
                "percent": meta.get("percent", 10),
                "message": meta.get("message", "처리 중..."),
            })

        if state == "SUCCESS":
            info = result.result or {}
            return JSONResponse({
                "state":        "SUCCESS",
                "percent":      100,
                "message":      "✅ 영상 완성!",
                "download_url": f"/api/kiosk/video/download/{task_id}",
                "duration_sec": info.get("total_duration_sec", 0),
                "file_size_mb": info.get("file_size_mb", 0),
                "script":       info.get("script_scenes", []),
            })

        if state == "FAILURE":
            return JSONResponse({
                "state":   "FAILURE",
                "percent": 0,
                "message": "❌ 영상 생성 실패. 다시 시도해 주세요.",
            })

        return JSONResponse({"state": state, "percent": 0, "message": "처리 중..."})

    except Exception as e:
        # Celery 연결 실패 → 파일 존재 여부로 완료 판단 (폴백)
        candidates = list(OUTPUT_DIR.glob(f"{task_id}*.mp4"))
        if candidates:
            mp4 = candidates[0]
            return JSONResponse({
                "state":        "SUCCESS",
                "percent":      100,
                "message":      "✅ 영상 완성!",
                "download_url": f"/api/kiosk/video/download/{task_id}",
                "file_size_mb": round(mp4.stat().st_size / 1_048_576, 1),
            })
        return JSONResponse({
            "state":   "PROGRESS",
            "percent": 50,
            "message": "🎬 영상 렌더링 중...",
        })


# ── 완성 영상 스트리밍 (플레이어용) ───────────────────────────
@router.get("/api/kiosk/video/stream/{task_id}")
async def stream_video(task_id: str):
    """브라우저 <video> 태그에서 바로 재생 가능한 스트리밍 엔드포인트."""
    candidates = list(OUTPUT_DIR.glob(f"{task_id}*.mp4"))
    if not candidates:
        return JSONResponse(
            status_code=404,
            content={"error": "영상 파일 없음"}
        )
    mp4 = max(candidates, key=lambda p: p.stat().st_mtime)
    return FileResponse(
        path=str(mp4),
        media_type="video/mp4",
        # Content-Disposition 없음 → 브라우저 인라인 재생
    )


# ── 완성 영상 다운로드 ──────────────────────────────────────────
@router.get("/api/kiosk/video/download/{task_id}")
async def download_video(task_id: str):
    """MP4 파일 강제 다운로드 엔드포인트."""
    candidates = list(OUTPUT_DIR.glob(f"{task_id}*.mp4"))
    if not candidates:
        return JSONResponse(
            status_code=404,
            content={"error": "영상을 찾을 수 없습니다. 잠시 후 다시 시도해 주세요."}
        )
    mp4 = max(candidates, key=lambda p: p.stat().st_mtime)
    fname = f"동네비서_광고_{task_id[:8]}.mp4"
    return FileResponse(
        path=str(mp4),
        media_type="video/mp4",
        filename=fname,
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


# ── 헬퍼 ────────────────────────────────────────────────────────
def _default_images() -> list[str]:
    """기본 배경 이미지 반환 (없으면 빈 리스트)."""
    imgs = [p for p in DEFAULT_IMAGES if Path(p).exists()]
    if imgs:
        return imgs
    # static/kiosk_assets에도 없으면 output 폴더에서 최근 이미지 시도
    fallbacks = sorted(OUTPUT_DIR.glob("*.jpg"), key=lambda p: p.stat().st_mtime, reverse=True)
    return [str(p) for p in fallbacks[:3]]
