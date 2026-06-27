from flask import Flask, request, jsonify
import cloudscraper
from bs4 import BeautifulSoup

app = Flask(__name__)

# প্রোডাকশন লেভেল স্ক্র্যাপার কনফিগারেশন
def create_premium_scraper():
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'android',
            'desktop': False
        }
    )
    # curl রিকোয়েস্টের সাথে সামঞ্জস্যপূর্ণ স্ট্যান্ডার্ড হেডার্স
    scraper.headers.update({
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'max-age=0',
        'Origin': 'https://pakistandatabase.com',
        'Referer': 'https://pakistandatabase.com/',
        'Sec-Ch-Ua': '"Android WebView";v="149", "Chromium";v="149"',
        'Sec-Ch-Ua-Mobile': '?1',
        'Sec-Ch-Ua-Platform': '"Android"',
        'X-Requested-With': 'mark.via.gp'
    })
    return scraper

scraper = create_premium_scraper()
TARGET_BASE = "https://pakistandatabase.com"

# --- Advanced HTML Parsing Logic ---
def parse_html(html, mode):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table: 
        return []
    
    rows = table.find_all("tr")
    results = []
    
    for tr in rows[1:]:
        cols = [td.get_text(strip=True) for td in tr.find_all("td")]
        if not cols: 
            continue
        
        # মোড অনুযায়ী ডেটা প্রসেসিং ও ফরম্যাটিং
        if mode == "standard":
            results.append({
                "mobile": cols[0] if len(cols) > 0 else "",
                "name": cols[1] if len(cols) > 1 else "",
                "cnic": cols[2] if len(cols) > 2 else "",
                "address": cols[3] if len(cols) > 3 else ""
            })
        elif mode == "police":
            results.append({
                "cnic": cols[0] if len(cols) > 0 else "",
                "name": cols[1] if len(cols) > 1 else "",
                "father_name": cols[2] if len(cols) > 2 else "",
                "address": cols[3] if len(cols) > 3 else "",
                "details": cols[4] if len(cols) > 4 else ""
            })
        elif mode == "landline":
            results.append({
                "number": cols[0] if len(cols) > 0 else "",
                "name": cols[1] if len(cols) > 1 else "",
                "address": cols[2] if len(cols) > 2 else "",
                "area": cols[3] if len(cols) > 3 else ""
            })
            
    return results

# --- Core Premium Fetch Engine ---
def execute_request(endpoint, query, turnstile_response, mode):
    try:
        url = f"{TARGET_BASE}/{endpoint}"
        
        # ক্লাউডফ্লেয়ার কুকি জেনারেট করার জন্য প্রথমে বেস ইউআরএল হিট করা
        scraper.get(TARGET_BASE, timeout=15)
        
        # পেলোড তৈরি (যেখানে ক্লাউডফ্লেয়ার টার্নস্টাইল টোকেন পাস করা হচ্ছে)
        payload = {
            'search_query': query,
            'cf-turnstile-response': turnstile_response
        }
        
        # ডাটা সাবমিট
        response = scraper.post(url, data=payload, timeout=30)
        
        if response.status_code == 200:
            parsed_data = parse_html(response.text, mode)
            return {
                "status": "success",
                "count": len(parsed_data),
                "data": parsed_data
            }
        
        return {
            "status": "failed", 
            "error": f"Target server responded with status {response.status_code}"
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

# --- Premium API Endpoints ---

@app.route('/api/fetch-data', methods=['POST'])
def fetch_data():
    req_data = request.get_json()
    
    # ইনপুট ভ্যালিডেশন
    query = req_data.get('query')
    turnstile_response = req_data.get('cf-turnstile-response')
    db_type = req_data.get('type') # 'mobile', 'cnic', 'police', 'landline'
    
    if not query or not turnstile_response or not db_type:
        return jsonify({
            "status": "error", 
            "message": "Missing required fields: 'query', 'cf-turnstile-response', and 'type' are mandatory."
        }), 400

    # এন্ডপয়েন্ট ও মোড ম্যাপিং
    endpoint_map = {
        "mobile": ("databases/sim.php", "standard"),
        "cnic": ("databases/cnic.php", "standard"),
        "police": ("databases/police.php", "police"),
        "landline": ("databases/landline.php", "landline")
    }
    
    if db_type not in endpoint_map:
        return jsonify({"status": "error", "message": "Invalid type provided."}), 400
        
    endpoint, mode = endpoint_map[db_type]
    
    # এক্সিকিউশন
    result = execute_request(endpoint, query, turnstile_response, mode)
    return jsonify(result)

if __name__ == '__main__':
    # প্রোডাকশন বা লোকাল হোস্ট এনভায়রনমেন্টে রান করার জন্য
    app.run(host='0.0.0.0', port=5000, debug=False)
