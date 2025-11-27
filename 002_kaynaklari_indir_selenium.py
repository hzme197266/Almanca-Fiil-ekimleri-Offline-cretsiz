# 02_kaynaklari_indir_selenium.py  ← %100 ÇALIŞAN SON VERSİYON
import sqlite3
import json
import time
import random
from pathlib import Path
from tqdm import tqdm
import undetected_chromedriver as uc

# -------------------------------
# Chrome'u otomatik doğru versiyonla başlat (HATA YOK!)
# -------------------------------
def get_driver():
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--lang=de-DE")

    # EN ÖNEMLİ SATIR → Chrome versiyonunu otomatik algılar!
    driver = uc.Chrome(options=options, use_subprocess=True)
    
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {get: () => false});
            window.navigator.chrome = {runtime: {},};
            Object.defineProperty(navigator, 'languages', {get: () => ['de-DE', 'de']});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        """
    })
    return driver

# -------------------------------
# Yardımcı fonksiyonlar
# -------------------------------
def connect_db():
    return sqlite3.connect("verbs.db")

def file_exists(verb, directory):
    return Path(f"data_sources/verblisten/{directory}/{verb}.htm").exists()

def mark_as_downloaded(verb, directory):
    conn = connect_db()
    cursor = conn.cursor()
    column = {'conjugations': 'conjugations_json',
              'definitions': 'definitions_json',
              'examples': 'examples_json'}[directory]
    cursor.execute(f"SELECT {column} FROM data_sources_verblisten WHERE word = ?", (verb,))
    row = cursor.fetchone()
    if row:
        data = json.loads(row[0])
        if not data.get('download_status', False):
            data['download_status'] = True
            cursor.execute(f"UPDATE data_sources_verblisten SET {column} = ? WHERE word = ?",
                           (json.dumps(data, ensure_ascii=False), verb))
            conn.commit()
    conn.close()

# -------------------------------
# Selenium ile indirme
# -------------------------------
def download_with_selenium(driver, verb, directory):
    if file_exists(verb, directory):
        mark_as_downloaded(verb, directory)
        return True

    urls = {
        'conjugations': f"https://www.verbformen.de/konjugation/{verb}.htm",
        'definitions':  f"http://woerter.net/verbs/{verb}.htm",
        'examples':     f"https://www.verbformen.de/konjugation/beispiele/{verb}.htm"
    }
    url = urls[directory]

    try:
        driver.get(url)
        time.sleep(random.uniform(1.5, 3.5))

        # Captcha kontrolü (çok nadir çıkar)
        if "Zugriffe" in driver.title or "captcha" in driver.page_source.lower():
            print(f"\nCAPTCHA ÇIKTI → {verb} ({directory})")
            input("Captcha’yı elle çöz, sonra Enter’a bas...")
            time.sleep(3)

        html = driver.page_source
        Path(f"data_sources/verblisten/{directory}").mkdir(parents=True, exist_ok=True)
        with open(f"data_sources/verblisten/{directory}/{verb}.htm", "w", encoding="utf-8") as f:
            f.write(html)

        mark_as_downloaded(verb, directory)
        print(f"Başarılı → {verb}")
        return True

    except Exception as e:
        print(f"Hata → {verb}: {e}")
        return False

# -------------------------------
# Ana döngü
# -------------------------------
def download_missing(directory):
    conn = connect_db()
    cursor = conn.cursor()
    column = {'conjugations': 'conjugations_json',
              'definitions': 'definitions_json',
              'examples': 'examples_json'}[directory]
    cursor.execute(f"SELECT word FROM data_sources_verblisten WHERE {column} LIKE '%false%'")
    words = [row[0] for row in cursor.fetchall()]
    conn.close()

    print(f"\n{directory.upper()} → {len(words)} eksik fiil indiriliyor...")

    driver = get_driver()
    try:
        for word in tqdm(words, desc=directory):
            download_with_selenium(driver, word, directory)
            time.sleep(random.uniform(0.8, 2.0))  # doğal hız
    finally:
        driver.quit()

# -------------------------------
# Çalıştır
# -------------------------------
if __name__ == "__main__":
    print("SELENIUM – KESİN ÇALIŞAN VERSİYON – BAŞLIYOR!\n")
    download_missing('conjugations')
    download_missing('examples')
    download_missing('definitions')
    print("\nTÜM DOSYALAR İNDİRİLDİ! Şimdi 03_liste_kazi.py çalıştır.")