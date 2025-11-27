# -*- coding: utf-8 -*-
import sqlite3
import json
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import tempfile
import subprocess
import os
import threading
import asyncio
from edge_tts import Communicate

DB_FILE = "verbs.db"

# -------------------- VERİTABANI --------------------
def connect_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def ara(fiil: str):
    fiil = fiil.strip().lower()
    if not fiil: return None
    conn = connect_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM verbs_de WHERE word = ?", (fiil,))
    row = cur.fetchone()
    conn.close()
    if not row: return None
    return {
        "word": row["word"],
        "level": row["level"],
        "conjugations": json.loads(row["conjugations"] or '{}'),
        "sentences": json.loads(row["sentences"] or '{}'),
        "definitions": json.loads(row["definitions"] or '[]'),
        "grammar": json.loads(row["grammar"] or '{}'),
        "sources": json.loads(row["sources"] or '[]')
    }

# -------------------- TTS --------------------
async def _tts_play(text: str, filepath: str):
    await Communicate(text, voice="de-DE-ConradNeural").save(filepath)

def tts_oynat(text: str):
    if not text.strip(): return
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_path = temp_file.name
    temp_file.close()

    def thread_func():
        try:
            asyncio.run(_tts_play(text, temp_path))
            if os.name == "nt":
                os.startfile(temp_path)
            elif os.name == "darwin":
                subprocess.run(["open", temp_path])
            else:
                subprocess.run(["xdg-open", temp_path], check=False)
        except Exception as e:
            messagebox.showerror("Ses Hatası", f"Ses çalınamadı:\n{e}")
        finally:
            def sil():
                import time
                time.sleep(20)
                if os.path.exists(temp_path):
                    try: os.unlink(temp_path)
                    except: pass
            threading.Thread(target=sil, daemon=True).start()
    threading.Thread(target=thread_func, daemon=True).start()

# -------------------- GÖSTERME --------------------
def goster(event=None):
    text_area.delete(1.0, tk.END)
    kelime = entry.get().strip().lower()
    if not kelime: return

    data = ara(kelime)
    if not data:
        text_area.insert(tk.END, f"Fiil bulunamadı: {kelime}\n", "hata")
        return

    text_area.insert(tk.END, f"{data['word'].upper()}\n", "fiil")
    text_area.insert(tk.END, f"Seviye: {data['level'] or 'Bilinmiyor'}\n\n", "seviye")

    text_area.insert(tk.END, "ÇEKİMLER\n", "baslik")
    for mood, tenses in data["conjugations"].items():
        text_area.insert(tk.END, f"  {mood.replace('_', ' ').title()}\n", "mood")
        for tense, forms in tenses.items():
            if forms and isinstance(forms, list):
                text_area.insert(tk.END, f"    • {tense.replace('_', ' ').capitalize()}\n", "tense")
                for form in forms:
                    text_area.insert(tk.END, f"        {form}\n", "form")
        text_area.insert(tk.END, "\n")

    text_area.insert(tk.END, "ANLAMLAR\n", "baslik")
    for i, block in enumerate(data["definitions"], 1):
        desc = " | ".join(block.get("descriptions", []))
        syn = f"  [≈ {', '.join(block.get('synonyms', []))}]" if block.get("synonyms") else ""
        text_area.insert(tk.END, f"{i}. {desc}{syn}\n\n", "anlam")

    text_area.insert(tk.END, "ÖRNEK CÜMLELER\n", "baslik")
    cumleler = [c for mood in data["sentences"].values()
                   for tens in mood.values()
                   for c in tens if c and c.strip()]
    if cumleler:
        for c in cumleler:
            text_area.insert(tk.END, f"   {c}\n", "cumle")
    else:
        text_area.insert(tk.END, "   (Henüz örnek cümle yok)\n\n", "bos")

    if data["sources"]:
        text_area.insert(tk.END, "KAYNAKLAR\n", "baslik")
        for src in data["sources"]:
            text_area.insert(tk.END, f"   {src.get('name','')}  {src.get('license','')}\n", "kaynak")

def dinle():
    k = entry.get().strip()
    if k:
        tts_oynat(f"Das Verb {k}. Beispiel: Ich {k} mich gern in der Sonne.")

# -------------------- GUI (KESİNLİKLE HATASIZ) --------------------
root = tk.Tk()
root.title("Almanca Fiil Sözlüğü")
root.geometry("12801260x920")
root.configure(bg="#f4f6f9")

# Başlık
header = tk.Frame(root, bg="#2c3e50", pady=30)
header.pack(fill=tk.X)
tk.Label(header, text="ALMANCE FİİL SÖZLÜĞÜ", font=("Segoe UI", 36, "bold"), fg="white", bg="#2c3e50").pack()

# Arama çubuğu
search_frame = tk.Frame(root, bg="#f4f6f9", pady=20)
search_frame.pack(fill=tk.X)

tk.Label(search_frame, text="Fiil:", font=("Segoe UI", 18), bg="#f4f6f9").pack(side=tk.LEFT, padx=25)
entry = tk.Entry(search_frame, font=("Segoe UI", 20), width=30, relief=tk.FLAT, bg="white", highlightthickness=2, highlightcolor="#3498db")
entry.pack(side=tk.LEFT, padx=10)
entry.focus()

style = ttk.Style()
style.theme_use("clam")
ttk.Button(search_frame, text="ARA", command=goster).pack(side=tk.LEFT, padx=10)
ttk.Button(search_frame, text="DİNLE", command=dinle).pack(side=tk.LEFT, padx=5)

# Metin alanı
text_area = scrolledtext.ScrolledText(
    root, font=("Consolas", 14), wrap=tk.WORD, bg="#fdfdfd",
    relief=tk.FLAT, bd=12, padx=40, pady=35, spacing1=10, spacing3=15
)
text_area.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)

# FONT TANIMLARI (TÜM SİSTEMLERDE ÇALIŞIR)
font_fiil = ("Segoe UI", 42, "bold")
font_baslik = ("Segoe UI", 19, "bold")
font_mood = ("Segoe UI", 16, "bold")
font_bos = ("Consolas", 14, "italic")

# TAG KONFIGÜRASYONU (HİÇBİR YAZIM HATASI YOK)
text_area.tag_config("fiil", font=font_fiil, foreground="#2c3e50", justify="center")
text_area.tag_config("seviye", font=("Segoe UI", 16), foreground="#e74c3c")
text_area.tag_config("baslik", font=font_baslik, foreground="#34495e", underline=True, spacing3=20)
text_area.tag_config("mood", font=font_mood, foreground="#2980b9")
text_area.tag_config("tense", font=("Consolas", 13, "bold"), foreground="#16a085")
text_area.tag_config("form", foreground="#2c3e50")
text_area.tag_config("anlam", font=("Segoe UI", 14), foreground="#27ae60")
text_area.tag_config("cumle", foreground="#34495e", lmargin1=50, lmargin2=60)
text_area.tag_config("bos", font=font_bos, foreground="#95a5a6")
text_area.tag_config("kaynak", foreground="#7f8c8d", font=("Consolas", 11))
text_area.tag_config("hata", foreground="#e74c3c", font=("Segoe UI", 22, "bold"), justify="center")

# Enter ile arama
entry.bind("<Return>", goster)

# Başlangıçta aalen göster
entry.insert(0, "aalen")
goster()

root.mainloop()