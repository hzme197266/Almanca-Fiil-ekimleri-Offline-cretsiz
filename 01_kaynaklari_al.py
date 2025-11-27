#01_kaynaklari_al.py
import requests
import json
import sqlite3
from bs4 import BeautifulSoup

# ---------------------------------------
# SQLite Bağlantısı
# ---------------------------------------
def connect_db():
    conn = sqlite3.connect("verbs.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS data_sources_verblisten (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        word TEXT,
        conjugations_json TEXT,
        definitions_json TEXT,
        examples_json TEXT,
        scrape_status INTEGER
    )
    """)

    conn.commit()
    return conn


# ---------------------------------------
# Scraper Fonksiyonu
# ---------------------------------------
def get_data_sources():
    base_url = 'https://www.verblisten.de/listen/verben/anfangsbuchstabe/vollstaendig'
    alphabet = 'abcdefghijklmnopqrstuvwxzäöü'

    conn = connect_db()
    cursor = conn.cursor()

    for letter in alphabet:
        print(f"Harf işleniyor: {letter}")
        page_counter = 1

        while True:
            url = f'{base_url}-{page_counter}.html?i=^{letter}'
            print("Sayfa:", url)

            response = requests.get(url)

            # Sayfa hiç yoksa döngüyü sonlandır
            if response.status_code != 200:
                print("Sayfa bulunamadı, sonraki harfe geçiliyor...\n")
                break

            soup = BeautifulSoup(response.content, 'html.parser')
            columns = soup.find_all('div', class_='listen-spalte')

            # Bu sayfada hiç liste yoksa sonlandır
            if not columns:
                print("Liste bulunamadı, sonraki harfe geçiliyor...\n")
                break

            any_links_found = False

            for div in columns:
                links = div.find_all('a')

                if not links:
                    continue

                any_links_found = True

                for a in links:
                    word = a.get('title', '').replace("Konjugation ", "")

                    href = a.get('href') or ""

                    conjugation_url = href
                    definition_url = href.replace('verbformen.de/konjugation', 'woerter.net/verbs')
                    example_url = href.replace('.de/konjugation', '.de/konjugation/beispiele')

                    cursor.execute("""
                    INSERT INTO data_sources_verblisten
                    (word, conjugations_json, definitions_json, examples_json, scrape_status)
                    VALUES (?, ?, ?, ?, ?)
                    """, (
                        word,
                        json.dumps({"download_status": False, "url": conjugation_url}),
                        json.dumps({"download_status": False, "url": definition_url}),
                        json.dumps({"download_status": False, "url": example_url}),
                        0
                    ))

                    print("Eklendi:", word)

            conn.commit()

            if not any_links_found:
                print("Bu sayfada link yok, sonraki harfe geçiliyor...\n")
                break

            page_counter += 1

    conn.close()
    print("\nTÜM VERİLER BAŞARIYLA KAYDEDİLDİ ✔")


# ---------------------------------------
# Çalıştır
# ---------------------------------------
if __name__ == "__main__":
    get_data_sources()
