#03_liste_kazi.py
import json
from bs4 import BeautifulSoup
from pathlib import Path
from tqdm import tqdm
import sqlite3

# ---------------------------------------
# SQLite Bağlantısı
# ---------------------------------------
def connect_db():
    conn = sqlite3.connect("verbs.db")
    return conn

# ---------------------------------------
# WordScrape Sınıfı
# ---------------------------------------
class WordScrape:

    def __init__(self, word):
        self.word = word
        self.conn = connect_db()
        self.cursor = self.conn.cursor()
        self.scrape_verb()

    # Veriyi parse et ve kaydet
    def scrape_verb(self):
        data = {
            'word': self.word,
            'level': self.scrape_level(),
            'conjugations': self.scrape_conjugations(),
            'examples': self.scrape_examples(),
            'definitions': self.scrape_definitions(),
            'grammar': self.scrape_grammar(),
            'translations': self.scrape_translations(),
            'source': {
                'name': 'verbformen.de',
                'license': 'CC-BY-SA 3.0'
            }
        }

        # verbs_scraped tablosuna ekle
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS verbs_scraped (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT UNIQUE,
                data_json TEXT
            )
        """)
        self.cursor.execute("""
            INSERT OR REPLACE INTO verbs_scraped (word, data_json) VALUES (?, ?)
        """, (self.word, json.dumps(data, ensure_ascii=False)))
        self.conn.commit()

        # data_sources_verblisten scrape_status güncelle
        self.cursor.execute("""
            UPDATE data_sources_verblisten SET scrape_status=1 WHERE word=?
        """, (self.word,))
        self.conn.commit()

    # -----------------------------
    # Scrape Fonksiyonları
    # -----------------------------
    def scrape_translations(self):
        file_name = f'data_sources/verblisten/conjugations/{self.word}.htm'
        translations = []
        if Path(file_name).is_file():
            with open(file_name, "r", encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            for div in soup.find_all('div'):
                if div.has_attr('lang'):
                    language = div.get("lang")
                    for span in div.find_all('span'):
                        if span.contents:
                            translations.append({
                                "language": language,
                                "source": 'verbformen.de',
                                "license": 'CC-BY-SA 3.0',
                                "translation": span.contents[0]
                            })
        return translations

    def scrape_level(self):
        file_name = f'data_sources/verblisten/definitions/{self.word}.htm'
        if Path(file_name).is_file():
            with open(file_name, "r", encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            for section in soup.find_all('section'):
                if 'wNr' in (section.get('class') or []):
                    for b in section.find_all('b'):
                        return b.contents[0]
        return ''

    def scrape_grammar(self):
        file_name = f'data_sources/verblisten/definitions/{self.word}.htm'
        if Path(file_name).is_file():
            with open(file_name, "r", encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            definition = {
                'grammar': {'general': [], 'sometimes': []},
                'prepositions_and_context': [],
                'usage': self.scrape_definitions_usage(soup),
                'source': {'name': 'verbformen.de','license':'CC-BY-SA 3.0'}
            }
            section_count = 0
            for section in soup.find_all('section'):
                section_count += 1
                if section_count == 1:
                    sometimes = False
                    for div in section.find_all('div'):
                        if isinstance(div.get('class'), list) and 'rInf' in div.get('class'):
                            for span in div.find_all('span'):
                                if span.get('title') == 'sometimes also:':
                                    sometimes = True
                                    continue
                                if sometimes:
                                    definition['grammar']['sometimes'].append(span.get('title'))
                                else:
                                    definition['grammar']['general'].append(span.get('title'))
                    # prepositions and context
                    for div in section.find_all('div'):
                        if div.get('class') and 'wVal' in div.get('class'):
                            for span in div.find_all('span'):
                                if span.get('title'):
                                    definition['prepositions_and_context'].append(span.get('title'))
            return definition
        return ''

    def scrape_definitions(self):
        file_name = f'data_sources/verblisten/definitions/{self.word}.htm'
        definitions = []
        if Path(file_name).is_file():
            with open(file_name, "r", encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            for div in soup.find_all('div'):
                if div.get('class') and 'rAbschnitt' in div.get('class'):
                    for section in div.find_all('section'):
                        definition = {"visible": True, "source": {"name": "verbformen.de","license":"CC-BY-SA 3.0"}}
                        definitions.append(definition)
        return definitions

    def scrape_definitions_usage(self, soup):
        definitions = {}
        for div in soup.find_all('div'):
            if div.get('class') and 'rAbschnitt' in div.get('class'):
                for section in div.find_all('section'):
                    if 'wFlx' in (section.get('class') or []):
                        for div_inner in section.find_all('div'):
                            if div_inner.get('class') and 'wBstn' in div_inner.get('class'):
                                for div_inner2 in div_inner.find_all('div'):
                                    if div_inner2.get('class') and 'wBst1' in div_inner2.get('class'):
                                        for ul in div_inner2.find_all('ul'):
                                            usage = [a.get('href').replace('http://www.satzapp.de/?s=', '') for a in ul.find_all('a')]
                                            keyword = div_inner2.h3.contents[0].lower().replace(' ', '_').replace('-', '_')
                                            if not definitions.get(keyword):
                                                definitions[keyword] = usage
                                            else:
                                                definitions[keyword] += usage
        return definitions

    def scrape_conjugations(self):
        """
        Fiilin çekimlerini HTML'den güvenli şekilde parse eder.
        Beklenmedik formatlarda IndexError vermez.
        """
        file_name = f'data_sources/verblisten/conjugations/{self.word}.htm'
        if not Path(file_name).is_file():
            return ''

        with open(file_name, "r", encoding='utf-8') as f:
            soup = BeautifulSoup(f.read(), 'html.parser')

        lines = []
        for ul in soup.find_all('ul'):
            if ul.get('class') == ['rLst']:  # başlık listelerini atla
                continue
            for li in ul.find_all('li'):
                # güvenli parse
                text = li.get_text(separator=":", strip=True)
                parts = text.split(':', 1)
                if len(parts) > 1:
                    lines.append(parts[1].strip())
                else:
                    lines.append(parts[0].strip())

        # lines listesinin uzunluğu eksikse default boş listeler ekle
        while len(lines) < 19:
            lines.append('')

        # JSON yapısı oluştur
        conjugations = {
            'indicative_active': {
                'present': lines[0].split(', '),
                'imperfect': lines[1].split(', '),
                'perfect': lines[2].split(', '),
                'plusquamperfect': lines[3].split(', '),
                'future': lines[4].split(', '),
                'future_perfect': lines[5].split(', '),
            },
            'subjunctive_active': {
                'present': lines[6].split(', '),
                'imperfect': lines[7].split(', '),
                'perfect': lines[8].split(', '),
                'plusquamperfect': lines[9].split(', '),
                'future': lines[10].split(', '),
                'future_perfect': lines[11].split(', '),
            },
            'conditional_active': {
                'imperfect': lines[12].split(', '),
                'plusquamperfect': lines[13].split(', '),
            },
            'imperative_active': {
                'present': lines[14].split(', '),
            },
            'infinitive_participle_active': {
                'infinitive_1': lines[15].split(', '),
                'infinitive_2': lines[16].split(', '),
                'participle_1': lines[17].split(', '),
                'participle_2': lines[18].split(', '),
            },
            'source': {
                'name': 'verbformen.de',
                'license': 'CC-BY-SA 3.0'
            }
        }

        return conjugations



    def scrape_examples(self):
        file_name = f'data_sources/verblisten/examples/{self.word}.htm'
        examples = []
        if Path(file_name).is_file():
            with open(file_name, "r", encoding='utf-8') as f:
                soup = BeautifulSoup(f.read(), 'html.parser')
            for div in soup.find_all('div'):
                if div.get('class') == ['rAbschnitt']:
                    for tr in div.find_all('tr'):
                        row_example = ''
                        for a in tr.find_all('a'):
                            if a.get('target') == '_blank':
                                row_example = a.get('href').replace('http://www.satzapp.de/?s=', '')
                        examples.append(row_example)
        examples_ordered = {
            'indicative_active': {'present': examples[0:6]},
            'subjunctive_active': {'present': examples[36:42]},
            'source': {'name':'verbformen.de','license':'CC-BY-SA 3.0'}
        }
        return examples_ordered

# ---------------------------------------
# Eksik dosyaları scrape et
# ---------------------------------------
def scrape_missing_files():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT word FROM data_sources_verblisten WHERE scrape_status=0")
    words = [row[0] for row in cursor.fetchall()]
    for word in tqdm(words):
        WordScrape(word)

# ---------------------------------------
# Çalıştır
# ---------------------------------------
if __name__ == "__main__":
    scrape_missing_files()
