import feedparser
import requests
from bs4 import BeautifulSoup
import google.generativeai as genai
import json
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import time
import os

# ==========================================
# ⚙️ KEYS LOAD FROM GITHUB SECRETS
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
# AES Key ko string se bytes mein convert karna zaroori hai
AES_SECRET_KEY = os.environ.get("AES_SECRET_KEY").encode('utf-8') 

if not GEMINI_API_KEY or not AES_SECRET_KEY:
    print("Error: API Keys not found in Secrets!")
    exit()

# Initialize Gemini AI
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# Verified High-Quality RSS Feeds
FEEDS = {
    "Economics": [
        "https://search.cnbc.com/rs/search/combinedcms/view.xml?profile=120000000&id=10000664",
        "https://www.thehindubusinessline.com/economy/feeder/default.rss"
    ],
    "International_Affairs": [
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://techcrunch.com/category/space/feed/" 
    ],
    "Sports": [
        "https://www.espn.com/espn/rss/news"
    ]
}

SYSTEM_PROMPT = """
You are a strict Current Affairs expert for competitive exams (NDA, IBPS).
Read the provided news article text.

Rule 1: If the news is about entertainment, gossip, local crime, regular accidents, or domestic political bickering, you MUST output strictly a JSON like this:
{"status": "REJECTED"}

Rule 2: If the news is highly relevant (Global Economics, International Relations, Major Space/Tech Launches, International Sports tournaments), extract the core facts and output strictly in this JSON format:
{
  "status": "ACCEPTED",
  "topic": "Short clear title",
  "what": "Exactly what happened?",
  "who": "Key people, organizations, or countries involved",
  "where": "Location",
  "when": "Date or timeframe",
  "why_how": "The reason, method, or background behind the event",
  "takeaway": "One line summary for exam perspective"
}

Do NOT output any markdown blocks like ```json. Output ONLY the raw JSON string.
"""

def get_article_text(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        paragraphs = soup.find_all('p')
        text = " ".join([p.get_text() for p in paragraphs])
        return text[:3000] 
    except:
        return ""

def encrypt_data(data_dict):
    json_string = json.dumps(data_dict)
    cipher = AES.new(AES_SECRET_KEY, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(json_string.encode('utf-8'), AES.block_size))
    
    return {
        "encryption": "AES-256-CBC",
        "iv": base64.b64encode(cipher.iv).decode('utf-8'),
        "payload": base64.b64encode(ct_bytes).decode('utf-8')
    }

def run_engine():
    print("🚀 Starting Current Affairs Deep Engine on GitHub Actions...")
    final_report = []

    for category, urls in FEEDS.items():
        print(f"\n📂 Scanning Category: {category}")
        for feed_url in urls:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:
                print(f"    * Reading: {entry.title}")
                article_text = get_article_text(entry.link)
                if len(article_text) < 200:
                    continue
                
                try:
                    response = model.generate_content(f"{SYSTEM_PROMPT}\n\nArticle Text:\n{article_text}")
                    ai_text = response.text.strip()
                    if ai_text.startswith("```json"):
                        ai_text = ai_text[7:-3].strip()
                        
                    result_json = json.loads(ai_text)
                    if result_json.get("status") == "ACCEPTED":
                        result_json['category'] = category
                        result_json['source_link'] = entry.link
                        final_report.append(result_json)
                        print("      [+] ACCEPTED & Structured!")
                    else:
                        print("      [X] Rejected by AI")
                except Exception as e:
                    print(f"      [!] AI Error: {e}")
                
                time.sleep(2) 

    if final_report:
        encrypted_package = encrypt_data(final_report)
        with open("encrypted_news.json", "w") as f:
            json.dump(encrypted_package, f, indent=4)
        print("✅ Success! Data Encrypted and saved.")
    else:
        print("⚠️ No valid news found today.")

if __name__ == "__main__":
    run_engine()
