import json
import os
from deep_translator import GoogleTranslator

def translate_to_hindi(text):
    try:
        # Google ka free translator use kar rahe hain
        return GoogleTranslator(source='en', target='hi').translate(text)
    except Exception as e:
        print(f"❌ Translation Error: {e}")
        return text # Fail hone par English hi return karega

def process_and_save():
    if not os.path.exists("final_data.json"):
        print("🤷‍♂️ final_data.json nahi mili.")
        return

    with open("final_data.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    translated_data = []

    print(f"🌍 Translating {len(data)} articles to Hindi...")

    for art in data:
        # Sirf cleaning aur translation pe focus
        en_article = art.get("cleaned_news_article", "")
        en_bullets = art.get("cleaned_news_bullets", [])
        en_facts = art.get("static_facts", [])

        # Translation
        hi_article = translate_to_hindi(en_article)
        hi_bullets = [translate_to_hindi(b) for b in en_bullets]
        hi_facts = [translate_to_hindi(f) for f in en_facts]

        translated_data.append({
            "title": art.get("title", ""),
            "en": {
                "article": en_article,
                "bullets": en_bullets,
                "facts": en_facts
            },
            "hi": {
                "article": hi_article,
                "bullets": hi_bullets,
                "facts": hi_facts
            }
        })

    with open("GOLu_ga.json", "w", encoding="utf-8") as f:
        json.dump(translated_data, f, indent=4, ensure_ascii=False)
    
    print("✅ Successfully saved to GOLu_ga.json")

if __name__ == "__main__":
    process_and_save()