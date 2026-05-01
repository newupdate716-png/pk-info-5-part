from flask import Flask, request, jsonify
import os
import time
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# --- Configuration ---
TARGET_BASE = os.getenv("TARGET_BASE", "https://pakistandatabase.com").rstrip("/")
MIN_INTERVAL = 1.0
LAST_CALL = {"ts": 0.0}

COPYRIGHT_NOTICE = "👉🏻 @sakib01994"
CREDIT = "@Bj_devs & ABBAS"

# --- Utility Functions ---
def rate_limit_wait():
    """সার্ভার ব্লক হওয়া থেকে বাঁচতে ১ সেকেন্ড বিরতি নিশ্চিত করে।"""
    now = time.time()
    elapsed = now - LAST_CALL["ts"]
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)
    LAST_CALL["ts"] = time.time()

def get_session_headers(path):
    """টার্গেট সার্ভারের জন্য সঠিক হেডার তৈরি করে।"""
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        "Referer": f"{TARGET_BASE}{path}",
        "Origin": TARGET_BASE,
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded",
        "Upgrade-Insecure-Requests": "1"
    }

# --- Parsing Logic ---
def parse_html_table(html, mode):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        return []
    
    rows = table.find_all("tr")
    results = []
    
    # প্রথম রো সাধারণত হেডার হয়, তাই ১ থেকে শুরু
    for tr in rows[1:]:
        cols = [td.get_text(strip=True) for td in tr.find_all("td")]
        if not cols: continue
        
        if mode == "standard": # Mobile & CNIC
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
        session = requests.Session()
        resp = session.post(
            url, 
            headers=get_session_headers(path), 
            data={"search_query": query_value}, 
            timeout=30
        )
        resp.raise_for_status()
        return parse_html_table(resp.text, mode)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return []

# --- Endpoints ---

@app.route('/')
def home():
    return jsonify({
        "message": "Pakistan Database API - Premium Fixed",
        "status": "Online",
        "endpoints": ["/api/mobile", "/api/cnic", "/api/police", "/api/landline", "/health"],
        "copyright": COPYRIGHT_NOTICE
    })

@app.route('/health')
def health():
    return jsonify({"status": "healthy", "copyright": COPYRIGHT_NOTICE})

@app.route('/api/mobile', methods=['GET', 'POST'])
def mobile_lookup():
    query = request.args.get('query') or (request.json.get('query') if request.is_json else None)
    if not query: return jsonify({"error": "Missing query"}), 400
    
    # অটোমেটিক ফরম্যাট ফিক্সিং
    if query.startswith('0'): query = '92' + query[1:]
    
    results = fetch_data("/databases/sim.php", query, "standard")
    return jsonify({
        "success": True, "query": query, "results_count": len(results),
        "results": results, "copyright": COPYRIGHT_NOTICE, "credit": CREDIT
    })

@app.route('/api/cnic', methods=['GET', 'POST'])
def cnic_lookup():
    query = request.args.get('query') or (request.json.get('query') if request.is_json else None)
    if not query: return jsonify({"error": "Missing query"}), 400
    
    results = fetch_data("/databases/sim.php", query, "standard")
    return jsonify({
        "success": True, "query": query, "results_count": len(results),
        "results": results, "copyright": COPYRIGHT_NOTICE, "credit": CREDIT
    })

@app.route('/api/police', methods=['GET', 'POST'])
def police_lookup():
    query = request.args.get('query') or (request.json.get('query') if request.is_json else None)
    if not query: return jsonify({"error": "Missing query"}), 400
    
    results = fetch_data("/databases/police.php", query, "police")
    return jsonify({
        "success": True, "query": query, "results_count": len(results),
        "results": results, "copyright": COPYRIGHT_NOTICE, "credit": CREDIT
    })

@app.route('/api/landline', methods=['GET', 'POST'])
def landline_lookup():
    query = request.args.get('query') or (request.json.get('query') if request.is_json else None)
    if not query: return jsonify({"error": "Missing query"}), 400
    
    results = fetch_data("/databases/landline.php", query, "landline")
    return jsonify({
        "success": True, "query": query, "results_count": len(results),
        "results": results, "copyright": COPYRIGHT_NOTICE, "credit": CREDIT
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
