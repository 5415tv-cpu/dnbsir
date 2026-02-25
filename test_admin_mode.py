
import urllib.request

def check_url(mode):
    url = f"http://localhost:8080/admin?mode={mode}"
    try:
        with urllib.request.urlopen(url) as response:
            html = response.read().decode('utf-8')
            if '사장님 로그인' in html:
                print(f"Mode {mode}: Found '사장님 로그인'")
            if '내 손안의 동네비서' in html:
                print(f"Mode {mode}: Found '내 손안의 동네비서'")
    except Exception as e:
        print(f"Error fetching {url}: {e}")

print("Checking 'login' mode:")
check_url('login')
print("\nChecking 'signup' mode:")
check_url('signup')
