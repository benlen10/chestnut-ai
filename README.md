Absolutely! Here’s a well-structured README.md for your project, covering what ChestnutAI does, setup, CLI & FastAPI usage, and helpful PostgreSQL/CLI tips:

⸻

ChestnutAI

ChestnutAI is a local, privacy-focused knowledge engine that ingests your personal notes (txt, md, etc.), preprocesses them using a local Large Language Model (LLM, e.g. via Ollama), and lets you efficiently query your own data via both a CLI and a FastAPI server.
	•	Fast import: Load thousands of notes instantly—no LLM required during import.
	•	Efficient pre-processing: Summarize (and later, embed) notes in batches, as needed.
	•	Fast Q&A: Only summarized notes are used to efficiently answer your questions.
	•	Hybrid interface: Interact via CLI or HTTP API.
	•	Data stays local: All storage is in your own PostgreSQL instance.

⸻

Features
	•	Import folders of .txt, .md, and other text files.
	•	Pre-process (summarize) notes in batches or individually (run overnight, on demand, etc.).
	•	Ask questions: Only the most relevant notes (chosen via summary matching) are passed to the LLM.
	•	FastAPI endpoints: Upload, summarize, list, and query via HTTP.
	•	CLI for batch processing and scripting.

⸻

Requirements
	•	Python 3.9+
	•	Ollama running locally with a suitable model (e.g., llama3.1:8b)
	•	PostgreSQL running locally (default port 5432)
	•	Python packages: See requirements.txt

⸻

Installation
	1.	Clone the repo:

git clone https://github.com/yourusername/chestnut-ai.git
cd chestnut-ai


	2.	Install Python dependencies:

pip install -r requirements.txt


	3.	Start your PostgreSQL server:
	•	On macOS (with Homebrew):

brew services start postgresql


	•	Or using systemctl on Linux:

sudo systemctl start postgresql


	4.	Create the database:

createdb chestnutai


	5.	(Optional) Set environment variables for DB connection if needed:

export CHESTNUTAI_DB=chestnutai
export CHESTNUTAI_USER=yourusername
export CHESTNUTAI_PASS=yourpassword
export CHESTNUTAI_HOST=localhost
export CHESTNUTAI_PORT=5432


	6.	Start Ollama and pull your preferred model:

ollama pull llama3.1:8b
ollama run llama3.1:8b



⸻

Usage

CLI Usage

All commands are run as:

python chestnutai.py [command] [arguments]

Import Notes

Import all notes from a folder:

python chestnutai.py import-folder /path/to/notes_folder

Summarize Notes (Pre-processing)

Summarize all unsummarized notes (can be run repeatedly; safe to run in batches):

python chestnutai.py summarize

Summarize the first N unsummarized notes (batch processing):

python chestnutai.py summarize-first-n 10

Summarize a specific note by ID:

python chestnutai.py summarize-note 5

List Summaries

Show all note summaries and IDs:

python chestnutai.py list-summaries

Ask a Question

Ask a question and get an answer using only the most relevant notes:

python chestnutai.py ask "What did I write about travel?" --top 3


⸻

FastAPI Usage
	1.	Start the server:

uvicorn chestnutai:app --reload


	2.	Interactive API docs available at:
http://localhost:8000/docs

API Endpoints
	•	POST /upload-note/ — Upload a single note file.
	•	POST /summarize-all/ — Summarize all unsummarized notes (batch).
	•	POST /summarize-note/{note_id} — Summarize a specific note by ID.
	•	GET /summaries/ — List all note summaries.
	•	POST /ask/ — Ask a question (JSON: {"question": "...", "top_k": 3}).

Example API call with curl:

curl -F "file=@/path/to/note.txt" http://localhost:8000/upload-note/
curl -X POST "http://localhost:8000/ask/" -H "Content-Type: application/json" \
    -d '{"question": "What did I write about travel?", "top_k": 3}'


⸻

PostgreSQL Tips & Common Commands

Connect to Postgres:

psql -d chestnutai

List all databases:

psql -l

List all tables in your database:

\dt

Delete all notes:

DELETE FROM notes;

Drop (delete) the notes table (will be recreated on next run):

DROP TABLE IF EXISTS notes;

Drop and recreate the whole database:

psql -d postgres
DROP DATABASE IF EXISTS chestnutai;
CREATE DATABASE chestnutai;

Reset failed summaries (from failed LLM calls):

UPDATE notes SET summary = NULL WHERE summary LIKE 'Error querying LLM%';


⸻

Troubleshooting
	•	PostgreSQL “role does not exist”:
Create a new user with: createuser -s yourusername
	•	psql: database “yourusername” does not exist:
Connect to the correct DB: psql -d chestnutai
	•	Ollama not running:
Run ollama run llama3.1:8b in a separate terminal.
	•	No relevant notes found for your question:
Summarize notes first via summarize or API.

⸻

Roadmap / Ideas
	•	Add semantic search with embeddings for smarter note retrieval.
	•	Support for additional file formats (PDF, HTML, etc.).
	•	UI for visualizing and managing notes.
	•	Scheduled/automated background summarization.

⸻

License

MIT

⸻

Author

blenington

⸻