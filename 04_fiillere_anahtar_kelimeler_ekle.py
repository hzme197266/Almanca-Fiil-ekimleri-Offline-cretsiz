# 04_fiillere_anahtar_kelimeler_ekle.py
import sqlite3
import json
import re
from tqdm import tqdm

def connect_db():
    conn = sqlite3.connect("verbs.db")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def clean_form(form):
    """Tek bir çekim formunu temizler ve aramaya uygun hâle getirir."""
    if not form or not isinstance(form, str):
        return ""
    
    # 1. Parantez içini tamamen sil (du), [gehst] vs.
    form = re.sub(r"[\(\[\{].*?[\)\]\}]", "", form)
    
    # 2. Zamirleri sil (ich, du, er/sie/es, wir, ihr, Sie)
    form = re.sub(r"^(ich|du|er/sie/es|wir|ihr|Sie)\s+", "", form, flags=re.IGNORECASE)
    
    # 3. "ge + fiil" yapılarında ge'yi koru ama gereksizleri temizle
    form = form.strip()
    
    # 4. zu + infinitiv → "zu" kalmasın
    form = form.replace("zu ", "")
    
    # 5. Noktalı boşluk, fazla boşluk vs.
    form = form.replace("·", " ").replace("  ", " ").strip()
    
    # 6. Boşsa hiç ekleme
    if len(form) < 2:
        return ""
    
    return form.lower()  # küçük harf → arama kolaylığı

def extract_keywords_from_conjugations(conjugations):
    """Tüm çekimlerden akıllı anahtar kelimeler çıkarır."""
    keywords = set()  # tekrar olmasın diye set kullanıyoruz
    
    # Normalde tüm formları ekleyebilirsin ama bazıları çok uzun (aux + partizip)
    # Sadece temel formları alalım:
    important_sections = [
        conjugations.get("indicative_active", {}),
        conjugations.get("subjunctive_active", {}),
        conjugations.get("imperative_active", {}),
        conjugations.get("infinitive_participle_active", {}),
    ]
    
    for section in important_sections:
        if not section:
            continue
        for tense, forms in section.items():
            # "source" anahtarını atla
            if tense == "source":
                continue
            for form_list in forms if isinstance(forms, dict) else [forms]:
                if isinstance(form_list, list):
                    for form in form_list:
                        cleaned = clean_form(form)
                        if cleaned:
                            keywords.add(cleaned)
                else:
                    cleaned = clean_form(form_list)
                    if cleaned:
                        keywords.add(cleaned)
    
    return sorted(keywords)

def main():
    conn = connect_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT word, data_json FROM verbs_scraped")
    rows = cursor.fetchall()
    
    print(f"{len(rows)} fiile anahtar kelime ekleniyor...\n")
    
    for word, json_str in tqdm(rows, desc="Anahtar kelimeler ekleniyor"):
        try:
            data = json.loads(json_str)
            
            # Eski keywords varsa sil (tekrar çalıştırılabilir olsun)
            if "keywords" in data:
                del data["keywords"]
            
            # Çekimlerden anahtar kelimeleri çıkar
            conj = data.get("conjugations", {})
            if conj:
                keywords = extract_keywords_from_conjugations(conj)
            else:
                keywords = [word.lower()]
            
            # Fiilin kendisi daima ilk sırada olsun
            keywords = [word.lower()] + [k for k in keywords if k != word.lower()]
            
            # En fazla 50 anahtar kelime (Anki performansı için)
            data["keywords"] = keywords[:50]
            
            # Güncelle
            cursor.execute("""
                UPDATE verbs_scraped 
                SET data_json = ? 
                WHERE word = ?
            """, (json.dumps(data, ensure_ascii=False), word))
            
        except Exception as e:
            print(f"\nHata: {word} → {e}")
    
    conn.commit()
    conn.close()
    print("\nTüm fiillere anahtar kelimeler başarıyla eklendi!")

if __name__ == "__main__":
    main()