from flask import Flask, request, jsonify
import os
import re
import time
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# --- Configuration ---
TARGET_BASE = os.getenv("TARGET_BASE", "https://pakistandatabase.com")
TARGET_PATH = "/databases/sim.php"
POLICE_PATH = "/databases/police.php"
LANDLINE_PATH = "/databases/landline.php"
MIN_INTERVAL = 1.0
LAST_CALL = {"ts": 0.0}

COPYRIGHT_NOTICE = "👉🏻 @sakib01994"
CREDIT = "@sakib01994 & SB-SAKIB"

# --- Utility Functions ---
def rate_limit_wait():
    now = time.time()
    elapsed = now - LAST_CALL["ts"]
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)
    LAST_CALL["ts"] = time.time()

def get_headers(referer_path):
    return {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
        "Referer": f"{TARGET_BASE.rstrip('/')}{referer_path}",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/x-www-form-urlencoded",
    }

# --- Specific Parsers ---
def parse_results(html, mode):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table: return []
    rows = table.find_all("tr")
    results = []
    
    for tr in rows:
        cols = [td.get_text(strip=True) for td in tr.find_all("td")]
        if not cols or len(cols) < 2: continue
        
        if mode in ["mobile", "cnic"]:
            if len(cols) >= 4:
                results.append({"mobile": cols[0], "name": cols[1], "cnic": cols[2], "address": cols[3]})
        elif mode == "police":
            if len(cols) >= 4:
                results.append({
                    "cnic": cols[0], "name": cols[1], "father_name": cols[2], 
                    "address": cols[3], "crime": cols[4] if len(cols)>4 else "",
                    "station": cols[5] if len(cols)>5 else "", "status": cols[6] if len(cols)>6 else ""
                })
        elif mode == "landline":
            if len(cols) >= 3:
                results.append({"number": cols[0], "name": cols[1], "address": cols[2], "area": cols[3] if len(cols)>3 else ""})
    return results

# --- Endpoints ---

# 1. Health Check Endpoint
@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "healthy",
        "service": "Pakistan Database API",
        "copyright": COPYRIGHT_NOTICE
    })

# 2. Universal API Endpoint (Mobile, CNIC, Landline, Police)
@app.route('/api', methods=['GET'])
def main_api():
    try:
        number = request.args.get('number')
        cnic = request.args.get('cnic')
        police_query = request.args.get('police') # নতুন প্যারামিটার ফর পুলিশ
        
        query_value = ""
        mode = ""
        endpoint = TARGET_PATH

        # লজিক সিলেকশন
        if police_query:
            query_value = police_query.strip()
            endpoint = POLICE_PATH
            mode = "police"
        elif number:
            query_value = number.strip()
            if query_value.startswith('0') and len(query_value) <= 11:
                endpoint = LANDLINE_PATH
                mode = "landline"
            else:
                mode = "mobile"
        elif cnic:
            query_value = cnic.strip()
            mode = "cnic"
        else:
            return jsonify({"error": "Missing query parameter (number, cnic, or police)"}), 400

        rate_limit_wait()
        
        # রিকোয়েস্ট পাঠানো
        url = f"{TARGET_BASE.rstrip('/')}{endpoint}"
        resp = requests.post(url, headers=get_headers(endpoint), data={"search_query": query_value}, timeout=25)
        resp.raise_for_status()

        results = parse_results(resp.text, mode)

        return jsonify({
            "success": True,
            "query": query_value,
            "type": mode,
            "results_count": len(results),
            "results": results,
            "copyright": COPYRIGHT_NOTICE,
            "credit": CREDIT
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/')
def home():
    return jsonify({
        "message": "Premium API is Live",
        "endpoints": {
            "mobile": "/api?number=923xxx",
            "cnic": "/api?cnic=xxxxx",
            "landline": "/api?number=0xxxx",
            "police": "/api?police=xxxxx",
            "health": "/health"
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
