@echo off
echo ==================================================
echo 🎬 100%% 무인화 10분 다큐멘터리 공장 (Phase 2)
echo ==================================================
echo.
echo [1/4] 스토리 분석 및 부족한 사진 프롬프트 생성 (AI 작가)
echo [2/4] 부족한 사진 자동 스케치 (AI 화가 - SD 1.5)
echo [3/4] 150장 전체 동영상 렌더링 (AI 감독 - SVD)
echo [4/4] 150개 조각 병합 및 최종본 완성 (AI 편집자 - FFmpeg)
echo.

"C:\Users\A\AppData\Local\Programs\Python\Python310\python.exe" "C:\Users\A\Desktop\AI_Store\core_engine\master_documentary_pipeline.py"

echo.
echo 작업이 완료되었습니다! SVD_Output 폴더를 확인하세요.
pause
