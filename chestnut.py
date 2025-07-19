import argparse
import sqlite3
import requests
import os

# ---- Config ----
OLLAMA_URL = "http://localhost:11434/api/generate"
LLM_MODEL = "llama3.1:8b"
DB_FILE = "chestnutai.db"
SUPPORTED_EXTS = {'.txt', '.md', '.markdown', '.rst', '.log', '.text'}

# ---- DB Setup ----
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        content TEXT
    )
    """)
    conn.commit()
    conn.close()

def add_note(filename, content):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("INSERT INTO notes (filename, content) VALUES (?, ?)", (filename, content))
    conn.commit()
    conn.close()

def get_all_notes():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    cur.execute("SELECT id, content FROM notes")
    notes = cur.fetchall()
    conn.close()
    return notes

# ---- LLM Call ----
def query_llm(prompt, context=None):
    if context:
        prompt = f"Context:\n{context}\n\nQuestion: {prompt}"
    data = {
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    try:
        response = requests.post(OLLAMA_URL, json=data, timeout=60)
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception as e:
        return f"Error querying LLM: {e}"

# ---- CLI Actions ----
def import_folder(folder_path):
    imported = 0
    for root, dirs, files in os.walk(folder_path):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in SUPPORTED_EXTS:
                fpath = os.path.join(root, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        content = f.read()
                    add_note(os.path.relpath(fpath, folder_path), content)
                    print(f"Imported: {fpath}")
                    imported += 1
                except Exception as e:
                    print(f"Failed to import {fpath}: {e}")
    if imported == 0:
        print("No supported text files found.")
    else:
        print(f"Imported {imported} files.")

def ask_question(question):
    notes = get_all_notes()
    if not notes:
        print("No notes found in the database.")
        return
    context = "\n\n".join([n[1] for n in notes])
    print("Querying LLM... (may take a moment)")
    answer = query_llm(question, context)
    print(f"\nAnswer:\n{answer}")

# ---- Main CLI ----
def main():
    parser = argparse.ArgumentParser(description="ChestnutAI CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Import folder
    parser_import = subparsers.add_parser("import-folder", help="Import all supported files from a folder")
    parser_import.add_argument("folder", help="Folder containing notes")

    # Ask
    parser_ask = subparsers.add_parser("ask", help="Ask a question about your notes")
    parser_ask.add_argument("question", nargs="+", help="Your question (in quotes if multi-word)")

    args = parser.parse_args()

    init_db()

    if args.command == "import-folder":
        import_folder(args.folder)
    elif args.command == "ask":
        question = " ".join(args.question)
        ask_question(question)

if __name__ == "__main__":
    main()