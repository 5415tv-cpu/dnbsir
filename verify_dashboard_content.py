
import sqlite3
import requests
import sys

# 1. Get Store ID
conn = sqlite3.connect("database.db")
c = conn.cursor()
c.execute("SELECT store_id FROM stores ORDER BY created_at DESC LIMIT 1")
row = c.fetchone()
conn.close()

if not row:
    print("No stores found in DB")
    sys.exit(1)

store_id = row[0]
print(f"Testing with Store ID: {store_id}")

# 2. Request Dashboard
cookies = {"admin_session": store_id}
try:
    response = requests.get("http://localhost:8080/admin/dashboard", cookies=cookies)
except requests.exceptions.ConnectionError:
    print("Failed to connect to localhost:8080. Is the server running?")
    sys.exit(1)

if response.status_code != 200:
    print(f"Dashboard returned Check Failed: {response.status_code}")
    sys.exit(1)

html = response.text

# 3. Check for Citizen Items (Should NOT exist)
citizen_keyword = "단골 가게" # "Find Store"
if citizen_keyword in html:
    print(f"[FAIL] Found '{citizen_keyword}' in dashboard! Fix is NOT working.")
else:
    print(f"[PASS] '{citizen_keyword}' NOT found. Fix confirmed.")

# 4. Check for Merchant Items (Should exist)
merchant_keyword = "정산/지갑" # "Settlement/Wallet"
if merchant_keyword in html:
    print(f"[PASS] Found '{merchant_keyword}'. Merchant menu is visible.")
else:
    print(f"[FAIL] '{merchant_keyword}' NOT found! Merchant menu is hidden.")
    print("Dumping Tab Navigation HTML context:")
    start_idx = html.find("<!-- Tab Navigation")
    end_idx = html.find("<!-- Tab 8")
    if start_idx != -1:
        print(html[start_idx:start_idx+2000]) # Print typical length of nav
    else:
        print("Could not find Tab Navigation in HTML")

# 5. Check for Merged Content
if 'id="overview-content"' in html:
    print("[PASS] Found 'overview-content'. Home is merged correctly.")
else:
    print("[FAIL] 'overview-content' NOT found!")

# 6. Check for Empty Secondary Nav (Should be hidden for Merchant)
# This is hard to test via simple string check on rendered HTML without parsing, 
# but we can check if the surrounding div is conditionally rendered.
# If 'switchDashboardTab(\'home\', this)' is ABSENT, it means the button is gone.

# 7. Check regarding Nesting Issue
# We expect `</div>` followed by `<!-- Tab 2: Products -->` or `<div id="tab-products"`
if '</div>\n\n    <!-- Tab 2: Products -->' in html or '</div>\n    <div id="tab-products"' in html:
    print("[PASS] 'tab-products' seems to be outside 'tab-overview' (based on closing tag proximity).")
else:
    print("[WARNING] Could not definitively verify nesting structure via string match. Manual check recommended.")

