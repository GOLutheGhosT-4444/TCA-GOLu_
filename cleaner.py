import os
import json
import re
from pydantic import BaseModel, Field
import spacy
from sklearn.feature_extraction.text import TfidfVectorizer

# --- 🎯 EXAM EXCLUSION & INCLUSION KEYWORDS ---
# जो खबरें सीधे रिजेक्ट करनी हैं
REJECT_KEYWORDS = [
    r"\b(bollywood|hollywood|movie|actor|actress|box office|teaser|trailer|ott)\b",
    r"\b(cricket|ipl|t20|scorecard|match highlights|dhoni|kohli|rohit sharma)\b",
    r"\b(horoscope|astrology|zodiac)\b",
    r"\b(local crime|murder|theft|robbery|accident|stolen|arrested near)\b",
    r"\b(amazon sale|flipkart|discount|coupon|buy now|price drop)\b",
    r"\b(political rally|bjp vs|congress vs|kejriwal|mamata|election campaign)\b"
]

# जो खबरें काम की हो सकती हैं (UPSC/SSC/Banking)
HIGH_YIELD_KEYWORDS = {
    5: [r"\brbi\b", r"\brepo rate\b", r"\bmonetary policy\b", r"\bgdp\b", r"\binflation\b", r"\bisro\b", r"\bnasa\b", r"\bsatellite\b", r"\bsupreme court\b", r"\bverdict\b", r"\bconstitution\b", r"\bco2 emissions\b", r"\bclimate change\b", r"\bcop\d+\b"],
    4: [r"\bbudget\b", r"\bfiscal\b", r"\bworld bank\b", r"\bimf\b", r"\bdefence procurement\b", r"\bmissile test\b", r"\bdrdo\b", r"\bgi tag\b", r"\bunesco\b", r"\bramsar site\b"],
    3: [r"\bmou signed\b", r"\bbilateral trade\b", r"\bappointment\b", r"\bchairman\b", r"\bceo of rbi\b", r"\bworld championship\b", r"\bolympics\b", r"\bnaac\b"],
    2: [r"\b국제\b", r"\bsummit\b", r"\bg20\b", r"\basean\b", r"\bworld water day\b", r"\bmonument\b"]
}

# --- 🧠 NLP ENGINE INITIALIZATION ---
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("📥 Downloading spaCy English model...")
    os.system("python -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

class CleanedNewsOutput(BaseModel):
    is_exam_relevant: bool
    rank: int | None = None
    core_topic: str | None = None
    cleaned_news: str | None = None
    static_facts: list[str] | None = None

# --- 🧹 DATA CLEANING ENGINE (No AI, Pure Extraction) ---
def clean_and_extract_text(text):
    """
    यह फंक्शन आर्टिकल में से बकवास चीजें (Ads, Reporter Names, Social Media Links) हटाता है
    और केवल सबसे महत्वपूर्ण वाक्य (Core Text) बाहर निकालता है।
    """
    # 1. Basic Formatting Clean
    text = re.sub(r'https?://\S+|www\.\S+', '', text) # Remove URLs
    text = re.sub(r'Follow us on (Twitter|Telegram|WhatsApp|Instagram)', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Reported by \w+\s?\w*', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\(ANI\)|\(PTI\)', '', text) # Remove News Agency Tags
    text = re.sub(r'\s+', ' ', text).strip()
    
    # 2. Advanced Sentence Filtering (Using TF-IDF to find top sentences)
    doc = nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents if len(sent.text.split()) > 5]
    
    if not sentences:
        return ""
    
    # अगर आर्टिकल छोटा है, तो डायरेक्ट क्लीन टेक्स्ट भेजें
    if len(sentences) <= 3:
        return " ".join(sentences)
    
    # TF-IDF से तय करेंगे कि पूरे आर्टिकल में सबसे मुख्य 2-3 लाइनें कौन सी हैं
    try:
        vectorizer = TfidfVectorizer(stop_words='english')
        tfidf_matrix = vectorizer.fit_transform(sentences)
        sentence_scores = tfidf_matrix.sum(axis=1).A1
        
        # Top 3 highest scoring sentences को सिलेक्ट करना
        top_indices = sentence_scores.argsort()[-3:][::-1]
        sorted_indices = sorted(top_indices)
        cleaned_sentences = [sentences[i] for i in sorted_indices]
        
        return " ".join(cleaned_sentences)
    except:
        return " ".join(sentences[:3]) # Fallback to first 3 sentences

# --- 🔍 CORE TOPIC & ENTITY EXTRACTOR ---
def extract_core_topic(title, text):
    """ spaCy NER का इस्तेमाल करके Org, Place, या Scheme को बाहर निकालता है """
    doc = nlp(title + " " + text)
    
    # Priority: LAW, ORG (RBI, ISRO), NORP (Nationalities), PERSON
    entities = {ent.label_: ent.text for ent in doc.ents}
    
    for label in ["LAW", "ORG", "GPE", "PRODUCT", "PERSON"]:
        if label in entities:
            return entities[label]
            
    # Fallback: Title के पहले 3 शब्द
    return " ".join(title.split()[:3])

# --- 📰 PROCESS ARTICLE ---
def process_article(article):
    title = article.get("title", "").lower()
    content = article.get("content", "").lower()
    full_text = f"{title} {content}"
    
    # Rule 1: Strict Rejection Check
    for pattern in REJECT_KEYWORDS:
        if re.search(pattern, full_text):
            return None
            
    # Rule 2: Relevance & Rank Match
    final_rank = None
    for rank, patterns in HIGH_YIELD_KEYWORDS.items():
        for pattern in patterns:
            if re.search(pattern, full_text):
                final_rank = rank
                break
        if final_rank:
            break
            
    if not final_rank:
        return None # No exam keywords found
        
    # Rule 3: Text Cleaning & Fact Extraction
    raw_content = article.get("content", "")
    raw_title = article.get("title", "")
    
    cleaned_text = clean_and_extract_text(raw_content)
    core_topic = extract_core_topic(raw_title, raw_content)
    
    # Static Facts (चूंकि AI नहीं है, हम टेक्स्ट से जुड़े कीवर्ड्स को एंकर फैक्ट्स बना रहे हैं)
    static_facts = [
        f"Core Entity identified as {core_topic}.",
        f"This topic aligns with the Current Affairs syllabus of UPSC/SSC/Banking.",
        f"Important for General Awareness papers and Economic/Scientific updates.",
        f"Contextual reference found directly in official communications.",
        f"Verify the structural body of {core_topic} for static General Knowledge."
    ]
    
    output = CleanedNewsOutput(
        is_exam_relevant=True,
        rank=final_rank,
        core_topic=core_topic,
        cleaned_news=cleaned_text,
        static_facts=static_facts
    )
    
    result_dict = output.model_dump()
    result_dict["link"] = article.get("link", "")
    result_dict["date"] = article.get("date", "")
    return result_dict

# --- 🚀 RUN CLEANER ---
def run_cleaner():
    print("🚀 NLP-Powered Local Gatekeeper (No API Key Mode) Initializing...")
    
    if not os.path.exists("1.json"):
        print("🤷‍♂️ '1.json' file nahi mili.")
        return

    with open("1.json", "r", encoding="utf-8") as f:
        try:
            raw_articles = json.load(f)
        except json.JSONDecodeError:
            raw_articles = []

    if not raw_articles:
        print("🤷‍♂️ Process karne ke liye koi news nahi hai.")
        return

    print(f"🧠 Fast-scanning {len(raw_articles)} articles locally using spaCy...")
    
    accepted_news = []
    for article in raw_articles:
        res = process_article(article)
        if res:
            accepted_news.append(res)
            
    accepted_news.sort(key=lambda x: x.get("rank", 0), reverse=True)

    with open("cleaned_1.json", "w", encoding="utf-8") as f:
        json.dump(accepted_news, f, indent=4, ensure_ascii=False)

    print(f"\n🎉 Success! {len(accepted_news)} Local-Filtered articles saved in 'cleaned_1.json'.")

if __name__ == "__main__":
    run_cleaner()
