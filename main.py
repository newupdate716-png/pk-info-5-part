from flask import Flask, request, jsonify
import cloudscraper
from bs4 import BeautifulSoup
import time

app = Flask(__name__)

# Cloudscraper কনফিগারেশন: ব্রাউজার ফিঙ্গারপ্রিন্ট সেট করা
scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'android', 'desktop': False}
)

TARGET_BASE = "https://pakistandatabase.com"

# --- Parsing Logic (সকল সিস্টেমের জন্য) ---
def parse_html(html, mode):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table: return []
    
    rows = table.find_all("tr")
    results = []
    for tr in rows[1:]:
        cols = [td.get_text(strip=True) for td in tr.find_all("td")]
        if not cols: continue
        
        if mode == "standard":
            results.append({"mobile": cols[0], "name": cols[1], "cnic": cols[2], "address": cols[3] if len(cols)>3 else ""})
        elif mode == "police":
            results.append({"cnic": cols[0], "name": cols[1], "father_name": cols[2], "address": cols[3], "details": cols[4] if len(cols)>4 else ""})
        elif mode == "landline":
            results.append({"number": cols[0], "name": cols[1], "address": cols[2], "area": cols[3] if len(cols)>3 else ""})
    return results

# --- Fetch Engine ---
def execute_request(endpoint, query, mode):
    try:
        url = f"{TARGET_BASE}/{endpoint}"
        # প্রথমে একবার পেজটি ভিজিট করে সেশন কুকি সেট করা
        scraper.get(TARGET_BASE)
        
        # ডাটা পাঠানো
        response = scraper.post(url, data={'search_query': query}, timeout=30)
        
        if response.status_code == 200:
            return parse_html(response.text, mode)
        return {"error": f"Failed with status {response.status_code}"}
    except Exception as e:
        return {"error": str(e)}

# --- Endpoints ---

@app.route('/api/mobile', methods=['POST'])
def mobile():
    query = request.json.get('query')
    return jsonify(execute_request("databases/sim.php", query, "standard"))

@app.route('/api/cnic', methods=['POST'])
def cnic():
    query = request.json.get('query')
    return jsonify(execute_request("databases/cnic.php", query, "standard"))

@app.route('/api/police', methods=['POST'])
def police():
    query = request.json.get('query')
    return jsonify(execute_request("databases/police.php", query, "police"))

@app.route('/api/landline', methods=['POST'])
def landline():
    query = request.json.get('query')
    return jsonify(execute_request("databases/landline.php", query, "landline"))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
