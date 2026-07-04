// 탄탄제작소 홈페이지 기본 자바스크립트

document.addEventListener('DOMContentLoaded', function() {
    // 모든 폼에 대해 중복 제출 방지 로직 적용
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                // 버튼 중복 클릭 방지 (시각적 피드백 제공)
                setTimeout(() => {
                    submitBtn.disabled = true;
                    submitBtn.textContent = '처리 중...';
                    submitBtn.style.opacity = '0.7';
                }, 10);
            }
        });
    });
    
    // 키오스크 환경 특성상 알림 메시지는 사용자가 명확히 인지할 수 있도록 
    // 자동으로 숨기지 않고 유지하는 것을 기본으로 합니다.
});
