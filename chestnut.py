import os
import argparse
import re
import psycopg2
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import JSONResponse
import requests

# ---- Config ----
OLLAMA_URL = "http://localhost:11434/api/generate"
LLM_MODEL = "llama3.1:8b"
SUPPORTED_EXTS = {'.txt', '.md', '.markdown', '.rst', '.log', '.text'}
DB_CONN_INFO = {
    'dbname': os.getenv("CHESTNUTAI_DB", "chestnutai"),
    'user': os.getenv("CHESTNUTAI_USER", "blenington"),
    'password': os.getenv("CHESTNUTAI_PASS", ""),
    'host': os.getenv("CHESTNUTAI_HOST", "localhost"),
    'port': os.getenv("CHESTNUTAI_PORT", 5432)
}

# ---- DB Utils ----
def get_conn():
    return psycopg2.connect(**DB_CONN_INFO)

def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS notes (
                id SERIAL PRIMARY KEY,
                filename TEXT,
                content TEXT,
                summary TEXT
            );
            """)
            conn.commit()

def add_note(filename, content):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO notes (filename, content) VALUES (%s, %s)",
                (filename, content)
            )
            conn.commit()

def fetch_notes(missing_summary=False):
    with get_conn() as conn:
        with conn.cursor() as cur:
            if missing_summary:
                cur.execute("SELECT id, filename, content FROM notes WHERE summary IS NULL")
            else:
                cur.execute("SELECT id, filename, content, summary FROM notes")
            return cur.fetchall()

def update_summary(note_id, summary):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE notes SET summary = %s WHERE id = %s", (summary, note_id))
            conn.commit()

def fetch_all_summaries():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, filename, summary FROM notes WHERE summary IS NOT NULL")
            return cur.fetchall()

# ---- LLM ----
def query_llm(prompt, context=None):
    if context:
        prompt = f"Context:\n{context}\n\nQuestion: {prompt}"
    data = {
        "model": LLM_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    try:
        response = requests.post(OLLAMA_URL, json=data, timeout=120)
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except Exception as e:
        return f"Error querying LLM: {e}"

def summarize_text(content):
    prompt = f"Summarize this note in 1-2 sentences:\n\n{content}"
    return query_llm(prompt)

def score_summary(summary, question):
    summary_words = set(re.findall(r'\w+', summary.lower()))
    question_words = set(re.findall(r'\w+', question.lower()))
    return len(summary_words & question_words)

def top_relevant_notes(question, top_k=3):
    all_notes = fetch_notes()
    scored = []
    for _id, fname, content, summary in all_notes:
        if summary is None:
            continue
        score = score_summary(summary, question)
        scored.append((score, fname, content, summary))
    top = sorted(scored, reverse=True)[:top_k]
    return top

# ---- Core Logic ----
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
    print(f"Imported {imported} files.")

def summarize_notes(batch_size=5):
    notes = fetch_notes(missing_summary=True)
    print(f"Found {len(notes)} notes needing summaries.")
    for i, (note_id, fname, content) in enumerate(notes):
        print(f"Summarizing [{i+1}/{len(notes)}]: {fname}")
        summary = summarize_text(content)
        # Check for error response and only store if summary is valid
        if summary.startswith("Error querying LLM"):
            print(f"  Failed to summarize: {summary}")
            continue  # Do NOT update summary in DB
        update_summary(note_id, summary)
        print(f"  Summary: {summary[:80]}...")

def ask_question(question, top_k=3):
    top = top_relevant_notes(question, top_k)
    if not top or top[0][0] == 0:
        print("No relevant notes found for your question.")
        return
    context = ""
    for _, fname, content, summary in top:
        context += f"[{fname}]\n{content}\n\n"
    print("Querying LLM on these top notes:")
    for _, fname, _, summary in top:
        print(f"  - {fname}: {summary[:80]}...")
    answer = query_llm(question, context)
    print(f"\nAnswer:\n{answer}")

def list_summaries():
    notes = fetch_all_summaries()
    print("\nSummaries of Imported Notes:")
    for _, fname, summary in notes:
        print(f"\n{fname}:\n{summary}")

# ---- CLI ----
def run_cli():
    parser = argparse.ArgumentParser(description="ChestnutAI CLI (batch-friendly!)")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_import = subparsers.add_parser("import-folder", help="Import all supported files from a folder")
    parser_import.add_argument("folder", help="Folder containing notes")

    parser_summarize = subparsers.add_parser("summarize", help="Summarize all notes missing a summary")
    parser_summarize.add_argument("--batch-size", type=int, default=5, help="How many notes to summarize at once")

    parser_list = subparsers.add_parser("list-summaries", help="List summaries of imported notes")

    parser_ask = subparsers.add_parser("ask", help="Ask a question about your notes")
    parser_ask.add_argument("question", nargs="+", help="Your question")
    parser_ask.add_argument("--top", type=int, default=3, help="Number of relevant notes to consider")

    args = parser.parse_args()
    init_db()
    if args.command == "import-folder":
        import_folder(args.folder)
    elif args.command == "summarize":
        summarize_notes(batch_size=args.batch_size)
    elif args.command == "list-summaries":
        list_summaries()
    elif args.command == "ask":
        question = " ".join(args.question)
        ask_question(question, top_k=args.top)

# ---- FastAPI App ----
app = FastAPI()

@app.on_event("startup")
def startup():
    init_db()

@app.post("/upload-note/")
async def upload_note(file: UploadFile = File(...)):
    content = await file.read()
    try:
        decoded = content.decode("utf-8")
        add_note(file.filename, decoded)
        return {"status": "success"}
    except Exception as e:
        return JSONResponse(status_code=400, content={"status": "error", "detail": str(e)})

@app.post("/summarize-note/{note_id}")
def api_summarize_note(note_id: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT content FROM notes WHERE id = %s", (note_id,))
            row = cur.fetchone()
            if not row:
                return JSONResponse(status_code=404, content={"error": "Note not found"})
            content = row[0]
            summary = summarize_text(content)
            update_summary(note_id, summary)
            return {"note_id": note_id, "summary": summary}

@app.post("/summarize-all/")
def api_summarize_all():
    notes = fetch_notes(missing_summary=True)
    results = []
    for note_id, fname, content in notes:
        summary = summarize_text(content)
        update_summary(note_id, summary)
        results.append({"note_id": note_id, "filename": fname, "summary": summary})
    return results

@app.get("/summaries/")
def api_list_summaries():
    notes = fetch_all_summaries()
    return [{"id": _id, "filename": fname, "summary": summary} for _id, fname, summary in notes]

@app.post("/ask/")
def api_ask_question(question: str, top_k: int = 3):
    top = top_relevant_notes(question, top_k)
    if not top or top[0][0] == 0:
        return {"answer": "No relevant notes found for your question.", "used_notes": []}
    context = ""
    used_files = []
    for _, fname, content, summary in top:
        context += f"[{fname}]\n{content}\n\n"
        used_files.append({"filename": fname, "summary": summary})
    answer = query_llm(question, context)
    return {"answer": answer, "used_notes": used_files}

# ---- Entrypoint ----
if __name__ == "__main__":
    run_cli()