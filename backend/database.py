import json
import os
import sqlite3
from contextlib import contextmanager

DB_FILE = os.environ.get("DB_PATH", "ram_catalog.db")


def init_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            image_filename TEXT,
            extracted_data TEXT,
            cad_model_path TEXT
        )
        """
    )
    conn.commit()
    conn.close()


@contextmanager
def get_db_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def store_scan(image_filename, rag_matches, cad_path):
    with get_db_connection() as conn:
        conn.execute(
            "INSERT INTO scans (image_filename, extracted_data, cad_model_path) VALUES (?, ?, ?)",
            (image_filename, json.dumps(rag_matches), cad_path),
        )
        conn.commit()
