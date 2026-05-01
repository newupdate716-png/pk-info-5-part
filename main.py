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
CREDIT = "@Bj_devs & ABBAS"

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

# --- Parsers ---
def parse_generic_table(html):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table: return []
    
    rows = table.find_all("tr")
    results = []
    for tr in rows:
        cols = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cols) >= 4:
            results.append({
                "mobile/cnic": cols[0],
                "name": cols[1],
                "cnic/father": cols[2],
                "address": cols[3],
                "extra": cols[4] if len(cols) > 4 else ""
            })
    return results

# --- Main API Route ---
@app.route('/api', methods=['GET'])
def universal_api():
    try:
        # গেট মেথড থেকে প্যারামিটার নেওয়া
        number = request.args.get('number')
        cnic = request.args.get('cnic')
        
        query_value = ""
        target_endpoint = TARGET_PATH
        mode = "standard"

        if number:
            query_value = number.strip()
            # ল্যান্ডলাইন নাকি মোবাইল চেক
            if len(query_value) >= 9 and len(query_value) <= 10 and query_value.startswith('0'):
                target_endpoint = LANDLINE_PATH
                mode = "landline"
            else:
                mode = "mobile"
        elif cnic:
            query_value = cnic.strip()
            mode = "cnic"
        else:
            return jsonify({"error": "Please provide 'number' or 'cnic' parameter"}), 400

        rate_limit_wait()
        
        # রিকোয়েস্ট পাঠানো
        url = f"{TARGET_BASE.rstrip('/')}{target_endpoint}"
        resp = requests.post(
            url, 
            headers=get_headers(target_endpoint), 
            data={"search_query": query_value}, 
            timeout=25
        )
        resp.raise_for_status()

        # ডাটা পার্সিং (পুলিশ ডাটাবেস চেক করার জন্য অতিরিক্ত লজিক)
        results = parse_generic_table(resp.text)
        
        # যদি সাধারণ সার্চে কিছু না পাওয়া যায়, তবে অটোমেটিক পুলিশ ডাটাবেস ট্রাই করবে
        if not results and (mode == "mobile" or mode == "cnic"):
            police_resp = requests.post(
                f"{TARGET_BASE.rstrip('/')}{POLICE_PATH}",
                headers=get_headers(POLICE_PATH),
                data={"search_query": query_value},
                timeout=25
            )
            results = parse_generic_table(police_resp.text)
            mode = "police/crime_db"

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
        "status": "Online",
        "usage": "/api?number=92300xxxxxxx or /api?cnic=12345xxxxxxx",
        "copyright": COPYRIGHT_NOTICE
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
