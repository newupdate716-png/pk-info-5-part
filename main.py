from flask import Flask, request, jsonify
import os
import time
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# --- কনফিগারেশন ---
TARGET_BASE = os.getenv("TARGET_BASE", "https://pakistandatabase.com")
TARGET_PATH = "/databases/sim.php"
POLICE_PATH = "/databases/police.php"
LANDLINE_PATH = "/databases/landline.php"
MIN_INTERVAL = 1.0
LAST_CALL = {"ts": 0.0}

COPYRIGHT_NOTICE = "👉🏻 @sakib01994"
CREDIT = "@Bj_devs & ABBAS"

# --- ইউটিলিটি ফাংশন ---
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

# --- পার্সার লজিক (সব ডাটাবেসের জন্য) ---
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

# --- মেইন এপিআই এন্ডপয়েন্ট ---
@app.route('/api', methods=['GET'])
def api_service():
    try:
        # প্যারামিটার গ্রহণ
        number = request.args.get('number')
        cnic = request.args.get('cnic')
        police = request.args.get('police') # পুলিশ রেকর্ডের জন্য প্যারামিটার
        
        query_value = ""
        mode = ""
        endpoint = TARGET_PATH

        # প্যারামিটার অনুযায়ী মোড সিলেকশন
        if police:
            query_value = police.strip()
            endpoint = POLICE_PATH
            mode = "police"
        elif number:
            query_value = number.strip()
            # ল্যান্ডলাইন ডিটেকশন (যদি ০ দিয়ে শুরু হয়)
            if query_value.startswith('0'):
                endpoint = LANDLINE_PATH
                mode = "landline"
            else:
                mode = "mobile"
        elif cnic:
            query_value = cnic.strip()
            mode = "cnic"
        else:
            return jsonify({"error": "Missing parameter! Use 'number', 'cnic', or 'police'"}), 400

        rate_limit_wait()
        
        # ডাটা ফেচ করা
        url = f"{TARGET_BASE.rstrip('/')}{endpoint}"
        resp = requests.post(url, headers=get_headers(endpoint), data={"search_query": query_value}, timeout=25)
        resp.raise_for_status()

        data_list = parse_results(resp.text, mode)

        return jsonify({
            "success": True,
            "status": "Premium Mode",
            "query": query_value,
            "type": mode,
            "results_count": len(data_list),
            "data": data_list,
            "copyright": COPYRIGHT_NOTICE,
            "credit": CREDIT
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# --- হেলথ চেক এন্ডপয়েন্ট ---
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "running",
        "api": "Pakistan Database All-in-One",
        "copyright": COPYRIGHT_NOTICE,
        "credit": CREDIT
    })

# --- হোম পেজ ---
@app.route('/')
def index():
    return jsonify({
        "message": "Welcome to Premium Database API",
        "endpoints": {
            "mobile": "/api?number=92300xxxxxxx",
            "cnic": "/api?cnic=xxxxx",
            "police": "/api?police=xxxxx",
            "landline": "/api?number=0xxxxxx",
            "health": "/health"
        },
        "developer": COPYRIGHT_NOTICE
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
