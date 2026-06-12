from flask import Flask, request, jsonify
import os
import time
import cloudscraper
from bs4 import BeautifulSoup

app = Flask(__name__)

# --- Configuration ---
TARGET_BASE = os.getenv("TARGET_BASE", "https://pakistandatabase.com").rstrip("/")
MIN_INTERVAL = 3.0  # আরও কিছুটা নিরাপদ বিরতি
LAST_CALL = {"ts": 0.0}

COPYRIGHT_NOTICE = "👉🏻 @sakib01994"

# স্থায়ী সেশন ব্যবহার করা (প্রতিবার নতুন করে scraper তৈরি করলে ব্লক হওয়ার চান্স বাড়ে)
scraper = cloudscraper.create_scraper(
    delay=5,
    browser={
        'browser': 'chrome',
        'platform': 'android',
        'desktop': False
    }
)

def rate_limit_wait():
    now = time.time()
    elapsed = now - LAST_CALL["ts"]
    if elapsed < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - elapsed)
    LAST_CALL["ts"] = time.time()

def fetch_data(path, query_value, mode):
    rate_limit_wait()
    try:
        url = f"{TARGET_BASE}{path}"
        # ওয়েবসাইট সাধারণত hidden inputs চেক করে, তাই ডিরেক্ট ফর্ম ডাটা
        payload = {"search_query": query_value}
        
        # সেশন ব্যবহার করে POST রিকোয়েস্ট
        resp = scraper.post(
            url, 
            data=payload, 
            timeout=45
        )
        
        if resp.status_code != 200:
            return {"error": f"Status Code: {resp.status_code}"}
            
        return parse_html_table(resp.text, mode)
    except Exception as e:
        return {"error": str(e)}

def parse_html_table(html, mode):
    soup = BeautifulSoup(html, "html.parser")
    # অনেক সময় ডাটা টেবিলের পরিবর্তে ডিভ বা স্প্যান ট্যাগে থাকে, সেটি চেক করা জরুরি
    table = soup.find("table")
    if not table:
        return []
    
    rows = table.find_all("tr")
    results = []
    
    # ইনডেক্সিং এবং ডাটা এক্সট্রাকশন লজিক ঠিক করা হয়েছে
    for tr in rows[1:]:
        cols = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cols) < 3: continue
        
        # ডাটা ম্যাপিং
        results.append({
            "mobile": cols[0],
            "name": cols[1],
            "cnic": cols[2],
            "address": cols[3] if len(cols) > 3 else "N/A"
        })
    return results

@app.route('/api/mobile', methods=['GET', 'POST'])
def mobile_lookup():
    query = request.args.get('query') or (request.json.get('query') if request.is_json else None)
    if not query: return jsonify({"error": "Missing query"}), 400
    
    # ফরম্যাট ঠিক করা
    clean_query = query.replace(" ", "")
    if clean_query.startswith('0'): clean_query = '92' + clean_query[1:]
    
    results = fetch_data("/databases/sim.php", clean_query, "standard")
    return jsonify({"success": True, "results": results, "copyright": COPYRIGHT_NOTICE})

@app.route('/api/cnic', methods=['GET', 'POST'])
def cnic_lookup():
    query = request.args.get('query') or (request.json.get('query') if request.is_json else None)
    if not query: return jsonify({"error": "Missing query"}), 400
    
    results = fetch_data("/databases/sim.php", query, "standard")
    return jsonify({"success": True, "results": results, "copyright": COPYRIGHT_NOTICE})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
