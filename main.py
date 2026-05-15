from flask import Flask, request, jsonify
import os
import time
import cloudscraper  # requests এর বদলে এটি ব্যবহার করা হয়েছে
from bs4 import BeautifulSoup

app = Flask(__name__)

# --- Configuration ---
TARGET_BASE = os.getenv("TARGET_BASE", "https://pakistandatabase.com").rstrip("/")
MIN_INTERVAL = 2.0  # ক্লাউডফ্লেয়ারের জন্য বিরতি একটু বাড়ানো নিরাপদ
LAST_CALL = {"ts": 0.0}

COPYRIGHT_NOTICE = "👉🏻 @sakib01994"
CREDIT = "@sakib01994 & SB-SAKIB"

# Cloudscraper সেশন তৈরি (এটি অটোমেটিক ব্রাউজার ফিঙ্গারপ্রিন্ট সেট করে)
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'android',
        'desktop': False
    }
)

# --- Utility Functions ---
def rate_limit_wait():
    now = time.time()
    elapsed = now - LAST_CALL["ts"]
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)
    LAST_CALL["ts"] = time.time()

def get_session_headers(path):
    """আধুনিক এন্ড্রয়েড ব্রাউজারের হেডার"""
    return {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": f"{TARGET_BASE}/",
        "Origin": TARGET_BASE,
        "X-Requested-With": "mark.via.gp",
        "Upgrade-Insecure-Requests": "1"
    }

# --- Parsing Logic ---
def parse_html_table(html, mode):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        # যদি টেবিল না পায়, হতে পারে ডাটা নেই বা ব্লক করেছে
        return []
    
    rows = table.find_all("tr")
    results = []
    
    for tr in rows[1:]:
        cols = [td.get_text(strip=True) for td in tr.find_all("td")]
        if not cols: continue
        
        if mode == "standard":
            if len(cols) >= 4:
                results.append({
                    "mobile": cols[0],
                    "name": cols[1],
                    "cnic": cols[2],
                    "address": cols[3]
                })
        elif mode == "police":
            if len(cols) >= 4:
                results.append({
                    "cnic": cols[0],
                    "name": cols[1],
                    "father_name": cols[2],
                    "address": cols[3],
                    "crime_details": cols[4] if len(cols) > 4 else "",
                    "police_station": cols[5] if len(cols) > 5 else "",
                    "status": cols[6] if len(cols) > 6 else ""
                })
        elif mode == "landline":
            if len(cols) >= 3:
                results.append({
                    "number": cols[0],
                    "name": cols[1],
                    "address": cols[2],
                    "area": cols[3] if len(cols) > 3 else "",
                    "type": cols[4] if len(cols) > 4 else ""
                })
    return results

# --- Shared Fetch Function ---
def fetch_data(path, query_value, mode):
    rate_limit_wait()
    try:
        url = f"{TARGET_BASE}{path}"
        # POST ডাটা
        payload = {"search_query": query_value}
        
        # cloudscraper দিয়ে রিকোয়েস্ট পাঠানো
        resp = scraper.post(
            url, 
            headers=get_session_headers(path), 
            data=payload, 
            timeout=30
        )
        
        if resp.status_code == 403:
            return [{"error": "Cloudflare Blocked. Needs manual Turnstile solver."}]
            
        return parse_html_table(resp.text, mode)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

# --- Endpoints ---

@app.route('/')
def home():
    return jsonify({
        "message": "Pakistan Database API - CF Bypass Mode",
        "status": "Online",
        "copyright": COPYRIGHT_NOTICE
    })

@app.route('/api/mobile', methods=['GET', 'POST'])
def mobile_lookup():
    query = request.args.get('query') or (request.json.get('query') if request.is_json else None)
    if not query: return jsonify({"error": "Missing query"}), 400
    if query.startswith('0'): query = '92' + query[1:]
    
    results = fetch_data("/databases/sim.php", query, "standard")
    return jsonify({"success": True, "results": results, "copyright": COPYRIGHT_NOTICE})

@app.route('/api/cnic', methods=['GET', 'POST'])
def cnic_lookup():
    query = request.args.get('query') or (request.json.get('query') if request.is_json else None)
    if not query: return jsonify({"error": "Missing query"}), 400
    
    results = fetch_data("/databases/sim.php", query, "standard")
    return jsonify({"success": True, "results": results, "copyright": COPYRIGHT_NOTICE})

# ... অন্যান্য এন্ডপয়েন্ট (Police/Landline) একই ভাবে থাকবে ...

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
