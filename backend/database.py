import json, os, sqlite3
from contextlib import contextmanager
DB_FILE = os.environ.get("DB_PATH", "ram_catalog.db")
def init_db():
    with sqlite3.connect(DB_FILE, check_same_thread=False) as c:
        c.execute("CREATE TABLE IF NOT EXISTS scans (id INTEGER PRIMARY KEY, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, image_filename TEXT, extracted_data TEXT, cad_model_path TEXT)")
def store_scan(fn, data, path):
    with sqlite3.connect(DB_FILE, check_same_thread=False) as c:
        c.execute("INSERT INTO scans (image_filename, extracted_data, cad_model_path) VALUES (?, ?, ?)", (fn, json.dumps(data), path))
        c.commit()
