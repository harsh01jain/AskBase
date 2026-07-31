# AskBase — Natural Language SQL

Ask questions about your database in plain English. Fully local, privacy-first — no data leaves your machine.

## Prerequisites

Install these on the new laptop before starting:

| Tool | Version | Download |
|------|---------|----------|
| **Node.js** | v18+ | https://nodejs.org |
| **Python** | 3.10+ | https://python.org |
| **Docker Desktop** | Latest | https://docker.com/products/docker-desktop |
| **Ollama** | Latest | https://ollama.com |
| **Git** | Latest | https://git-scm.com |

## Quick Setup (New Laptop)

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/AskBase.git
cd AskBase
```

### 2. Pull the LLM model

```bash
ollama pull qwen2.5-coder:7b
```

This downloads ~4GB. Make sure Ollama is running in the background.

### 3. Start the database

```bash
docker-compose up -d postgres
```

This starts PostgreSQL on port `5433` and runs `init.sql` to create the read-only user.

### 4. Set up the backend

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env from template
copy .env.example .env     # Windows
# cp .env.example .env     # macOS/Linux

# Seed the database with sample data
python seed_db.py

# Start the backend
uvicorn main:app --reload --port 8000
```

### 5. Set up the frontend

Open a **new terminal**:

```bash
cd frontend

# Install dependencies
npm install

# Start the dev server
npm run dev
```

### 6. Open the app

Go to **http://localhost:3000** in your browser.

## Project Structure

```
AskBase/
├── backend/
│   ├── main.py            # FastAPI server + SSE query endpoint
│   ├── database.py        # PostgreSQL connection + schema introspection
│   ├── llm.py             # Ollama LLM integration (SQL generation)
│   ├── retrieval.py       # ChromaDB schema retrieval (RAG)
│   ├── seed_db.py         # Sample data seeder
│   ├── requirements.txt   # Python dependencies
│   └── .env.example       # Environment template
├── frontend/
│   ├── src/app/
│   │   ├── page.tsx       # Main chat UI
│   │   ├── layout.tsx     # Root layout
│   │   └── globals.css    # Design system
│   ├── tailwind.config.ts
│   └── package.json
├── docker-compose.yml     # PostgreSQL + full-stack Docker config
├── init.sql               # DB init (read-only user setup)
├── .env.example           # Root env template
└── README.md
```

## Environment Variables

### `backend/.env`

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_USER` | DB read-only user | `nl2sql_reader` |
| `POSTGRES_PASSWORD` | DB password | `yourpassword` |
| `POSTGRES_HOST` | DB host | `127.0.0.1` |
| `POSTGRES_PORT` | DB port | `5433` |
| `POSTGRES_DB` | Database name | `yourdatabase` |
| `OLLAMA_BASE_URL` | Ollama API URL | `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | LLM model name | `qwen2.5-coder:7b` |

## Troubleshooting

**"Connection refused" on backend start**
→ Make sure Docker Desktop is running and the postgres container is up: `docker ps`

**"Model not found" errors**
→ Run `ollama list` to check if the model is downloaded. If not: `ollama pull qwen2.5-coder:7b`

**Frontend shows no schema**
→ Backend must be running on port 8000. Check the terminal for errors.
