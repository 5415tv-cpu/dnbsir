import ai_manager

def test_routing():
    print("[*] Starting Model Routing Test...")
    
    # Test Cases
    cases = [
        ("안녕", "gemini-1.5-flash", "Short Greeting"),
        ("영업시간이 어떻게 되나요?", "gemini-1.5-flash", "Simple Question"),
        ("A와 B의 차이점을 상세하게 비교 분석해줘.", "gemini-1.5-pro", "Keyword '분석'"),
        ("이 문제의 원인을 파악하고 해결 방안을 기획해봐.", "gemini-1.5-pro", "Keywords '해결', '기획'"),
        ("A" * 101, "gemini-1.5-pro", "Length > 100")
    ]
    
    for text, expected, label in cases:
        result = ai_manager.determine_model_tier(text)
        if result == expected:
            print(f"[OK] {label}: Routed to {result}")
        else:
            print(f"[X] {label} Failed: Expected {expected}, got {result}")

if __name__ == "__main__":
    test_routing()
