# logger.py
# 동네비서 전용 로깅 모듈 - 날짜별 자동 분할 + 30일 자동 삭제
import logging
from logging.handlers import TimedRotatingFileHandler
import os

# 1. logs 폴더가 없으면 자동 생성
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)

# 2. 동네비서 전용 로거 생성
logger = logging.getLogger("dongnebiseo")

# 중복 핸들러 방지 (모듈 재로딩 시)
if not logger.handlers:
    logger.setLevel(logging.INFO)

    # 3. 날짜별 파일 분할 (매일 자정 갱신, 최대 30일 보관)
    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(LOG_DIR, "error.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    file_handler.suffix = "%Y-%m-%d"  # logs/error.log.2026-06-12 형태로 저장

    # 4. 정갈한 텍스트 포맷
    # [시간] | [위험도] | [발생위치:줄번호] | 메시지
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | [%(filename)s:%(lineno)d] | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 5. 터미널 콘솔에도 출력 (서버 디버깅용)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
