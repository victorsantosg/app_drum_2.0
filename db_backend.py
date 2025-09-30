import sqlite3
import json

DB_FILE = "grooves.db"

def init_db():
    """Cria a tabela de grooves se não existir."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS grooves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            bpm INTEGER NOT NULL,
            data TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def save_groove(name, bpm, sequence, timbres):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    data = {"sequence": sequence, "timbres": timbres}
    c.execute("INSERT INTO grooves (name, bpm, data) VALUES (?,?,?)",
              (name, bpm, json.dumps(data)))
    conn.commit()
    conn.close()

def load_all_grooves():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, name, bpm FROM grooves")
    rows = c.fetchall()
    conn.close()
    return rows

def load_groove_by_id(groove_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT data, bpm FROM grooves WHERE id = ?", (groove_id,))
    row = c.fetchone()
    conn.close()
    if row:
        return json.loads(row[0]), row[1]
    return None, None

def delete_groove(groove_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM grooves WHERE id = ?", (groove_id,))
    conn.commit()
    conn.close()
