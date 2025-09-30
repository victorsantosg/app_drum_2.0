import sqlite3
import json
import os
import sys
import traceback

# Se empacotado com PyInstaller, os arquivos de dados ficam em _MEIPASS
def resource_path(filename):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, filename)
    # usa o diretório do script (não o cwd) para caminhos relativos consistentes
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, filename)

DB_FILE = resource_path("grooves.db")

def init_db():
    """Cria a tabela de grooves se não existir."""
    try:
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
    except Exception:
        print("Erro ao inicializar DB:")
        traceback.print_exc()

def save_groove(name, bpm, sequence, timbres):
    """Salva um groove no banco. Retorna o id inserido ou None em erro."""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        data = {"sequence": sequence, "timbres": timbres}
        c.execute("INSERT INTO grooves (name, bpm, data) VALUES (?,?,?)",
                  (name, bpm, json.dumps(data)))
        conn.commit()
        last_id = c.lastrowid
        conn.close()
        return last_id
    except Exception:
        print("Erro ao salvar groove:")
        traceback.print_exc()
        return None

def load_all_grooves():
    """Retorna lista de grooves: id, nome, bpm."""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT id, name, bpm FROM grooves ORDER BY id DESC")
        rows = c.fetchall()
        conn.close()
        return rows
    except Exception:
        print("Erro ao carregar lista de grooves:")
        traceback.print_exc()
        return []

def load_groove_by_id(groove_id):
    """Carrega groove específico pelo ID. Retorna (data_dict, bpm) ou (None, None)."""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("SELECT data, bpm FROM grooves WHERE id = ?", (groove_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return json.loads(row[0]), row[1]
        return None, None
    except Exception:
        print(f"Erro ao carregar groove id={groove_id}:")
        traceback.print_exc()
        return None, None

def delete_groove(groove_id):
    """Deleta groove pelo ID."""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("DELETE FROM grooves WHERE id = ?", (groove_id,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        print(f"Erro ao deletar groove id={groove_id}:")
        traceback.print_exc()
        return False
