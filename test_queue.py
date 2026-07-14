from celery import Celery
import os

# 1. 워커와 동일한 Redis 큐(대기열) 주소를 세팅합니다.
# 워커 세팅 시 안티그라비티가 환경 변수(DONGNE_REDIS_URL)를 적용했으므로, 
# 동일하게 환경 변수를 불러오되, 테스트용 로컬 주소를 기본값으로 둡니다.
REDIS_URL = os.environ.get('DONGNE_REDIS_URL', 'redis://127.0.0.1:6379/0')

# Celery 앱 인스턴스 생성 (워커와 이름이 같아야 연결됩니다)
app = Celery('dongne_biseo_worker', broker=REDIS_URL, backend=REDIS_URL)

def run_test():
    print("==========================================================")
    print("🚀 [클라우드 시뮬레이터] 테스트 작업을 Redis 대기열로 전송합니다...")
    print("==========================================================")
    
    # 2. 워커에게 보낼 테스트 데이터 준비 (동네비서 홍보 영상 컨셉)
    test_kwargs = {
        'user_id': 'dongnebiseo_promo_001',
        'image_url': 'https://dnbsir.com/dummy_apple.jpg',
        'text_prompt': 'A promotional video showing a customer calling on a smartphone, a smiling farmer answering, a clean smartphone order UI, and a cheerful delivery driver delivering a package, cinematic lighting, 8k resolution'
    }
    
    # 3. app.send_task를 통해 워커(worker.render_short_form_video)에게 작업 지시!
    task_result = app.send_task(
        'worker.render_short_form_video', # 워커 파일(worker.py)에 등록된 함수 이름
        kwargs=test_kwargs
    )
    
    print(f"✅ 대기열 전송 완료! (발급된 작업 ID: {task_result.id})")
    print("⏳ 워커(Worker) 터미널 창을 확인해 보세요. RTX 4070이 작업을 시작했을 것입니다.")
    print("   결과가 나올 때까지 이 창에서 대기합니다... (최대 5분)")
    
    try:
        # 4. 워커가 일을 마칠 때까지 기다렸다가 결과(Return 값)를 받아옵니다.
        result = task_result.get(timeout=300)
        print("\n🎉 렌더링 작업이 성공적으로 완료되었습니다!")
        print(f"👉 워커가 보내온 최종 결과 데이터: {result}")
        
        # 바탕화면으로 파일 복사
        import shutil
        source_path = result.get('result')
        desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop', os.path.basename(source_path))
        if os.path.exists(source_path):
            shutil.copy2(source_path, desktop_path)
            print(f"✅ 바탕화면에 영상 저장이 완료되었습니다! 경로: {desktop_path}")
        else:
            print("⚠️ 원본 영상 파일을 찾을 수 없어 바탕화면 복사에 실패했습니다.")
            
    except Exception as e:
        print(f"\n❌ 작업 대기 중 오류가 발생했거나 타임아웃 되었습니다: {e}")
        print("워커 터미널 창의 에러 로그를 확인해 주십시오.")

if __name__ == '__main__':
    run_test()
