# AskBase — Natural Language to SQL

Ask questions about your database in plain English. Fully local, privacy-first — no data leaves your machine.

Built with **Next.js** (frontend), **FastAPI** (backend), **Ollama** (LLM), **PostgreSQL** (database), and **ChromaDB** (schema retrieval).

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Setup](#quick-setup)
- [Connecting to Your Own Database](#connecting-to-your-own-database)
- [Adding New Tables](#adding-new-tables)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Environment Variables](#environment-variables)
- [Docker (Full Stack)](#docker-full-stack)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

Install these before starting:

| Tool | Version | Download |
|------|---------|----------|
| **Node.js** | v18+ | https://nodejs.org |
| **Python** | 3.10+ | https://python.org |
| **Docker Desktop** | Latest | https://docker.com/products/docker-desktop |
| **Ollama** | Latest | https://ollama.com |
| **Git** | Latest | https://git-scm.com |

---

## Quick Setup

### 1. Clone the repo

```bash
git clone https://github.com/harsh01jain/AskBase.git
cd AskBase
```

### 2. Pull the LLM model

Make sure Ollama is running, then:

```bash
ollama pull qwen2.5-coder:7b
```

This downloads ~4GB. Verify it's available:

```bash
ollama list
```

### 3. Start the database

```bash
docker-compose up -d postgres
```

Verify it's running:

```bash
docker ps
```

You should see a `postgres:15` container on port `5433`.

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

# Create your .env from the template
copy .env.example .env          # Windows
cp .env.example .env            # macOS/Linux

# Seed the database with sample data (1000 customers, 50 products, 5000 orders)
python seed_db.py

# Start the backend server
uvicorn main:app --reload --port 8000
```

The backend runs at **http://localhost:8000**.

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

Go to **http://localhost:3000** in your browser and start asking questions!

---

## Connecting to Your Own Database

AskBase can connect to **any PostgreSQL database** — not just the demo one. Here's how:

### Option A: Connect to an existing PostgreSQL instance

Edit `backend/.env` with your database credentials:

```env
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_db_password
POSTGRES_HOST=your_db_host        # e.g. 127.0.0.1, localhost, or a remote IP
POSTGRES_PORT=5432                 # default PostgreSQL port
POSTGRES_DB=your_database_name
```

Then restart the backend:

```bash
cd backend
uvicorn main:app --reload --port 8000
```

The backend will automatically:
1. Connect to your database
2. Read all tables from the `public` schema
3. Index them into ChromaDB for AI retrieval
4. Display them in the sidebar

### Option B: Use Docker Compose with a different database

Edit `docker-compose.yml` and change the environment variables:

```yaml
postgres:
  image: postgres:15
  environment:
    POSTGRES_USER: your_admin_user
    POSTGRES_PASSWORD: your_admin_password
    POSTGRES_DB: your_database_name
```

Then update `init.sql` to create a read-only user for your database:

```sql
CREATE ROLE your_reader WITH LOGIN PASSWORD 'your_reader_password';
GRANT CONNECT ON DATABASE your_database_name TO your_reader;
GRANT USAGE ON SCHEMA public TO your_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO your_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO your_reader;
```

### Option C: Connect to a remote/cloud database

AskBase works with any PostgreSQL-compatible database (AWS RDS, Supabase, Neon, etc.). Just set the host, port, and credentials in `backend/.env`:

```env
POSTGRES_HOST=your-db.us-east-1.rds.amazonaws.com
POSTGRES_PORT=5432
POSTGRES_USER=readonly_user
POSTGRES_PASSWORD=your_password
POSTGRES_DB=production_db
```

> **Security note:** AskBase validates that only `SELECT` queries are executed. It will never run INSERT, UPDATE, DELETE, or DROP statements. For extra safety, always connect with a **read-only** database user.

### Re-indexing the schema

After connecting to a new database, re-index the schema so the AI knows about your tables:

```bash
curl -X POST http://localhost:8000/reindex
```

Or simply restart the backend — it auto-indexes on startup.

---

## Adding New Tables

### Method 1: Add tables directly via SQL

Connect to your PostgreSQL database and create tables:

```bash
# Connect using Docker
docker exec -it $(docker ps -q --filter ancestor=postgres:15) psql -U root -d yourdatabase

# Or connect using psql directly
psql -h 127.0.0.1 -p 5433 -U root -d yourdatabase
```

Then run your SQL:

```sql
CREATE TABLE employees (
    employee_id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    department VARCHAR(50),
    salary DECIMAL(10, 2),
    hire_date DATE
);

INSERT INTO employees (name, department, salary, hire_date) VALUES
('Alice Johnson', 'Engineering', 120000, '2022-03-15'),
('Bob Smith', 'Marketing', 85000, '2021-07-01'),
('Carol Williams', 'Engineering', 130000, '2020-11-20');
```

Grant read access to the app user:

```sql
GRANT SELECT ON employees TO nl2sql_reader;
```

Then re-index:

```bash
curl -X POST http://localhost:8000/reindex
```

Refresh the frontend — the new table appears in the sidebar and AskBase can now answer questions about it.

### Method 2: Add tables via the seed script

Edit `backend/seed_db.py` to add your table creation and data insertion logic. Then run:

```bash
cd backend
python seed_db.py
```

### Method 3: Import from a SQL dump

If you have an existing `.sql` dump file:

```bash
# Via Docker
docker exec -i $(docker ps -q --filter ancestor=postgres:15) psql -U root -d yourdatabase < your_dump.sql

# Via psql directly
psql -h 127.0.0.1 -p 5433 -U root -d yourdatabase < your_dump.sql
```

Then grant permissions and re-index:

```sql
GRANT SELECT ON ALL TABLES IN SCHEMA public TO nl2sql_reader;
```

```bash
curl -X POST http://localhost:8000/reindex
```

---

## API Reference

The backend exposes these endpoints at `http://localhost:8000`:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Check database and Ollama connectivity |
| `GET` | `/schema` | Returns all tables and columns from the `public` schema |
| `GET` | `/history` | Returns the last 50 query audit logs |
| `POST` | `/query` | Main endpoint — sends a question and streams back SQL + results via SSE |
| `POST` | `/reindex` | Re-indexes the database schema into ChromaDB |

### POST `/query` — Example

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question": "How many customers are there?", "history": []}'
```

Response is a **Server-Sent Events (SSE)** stream with these event types:

| Event Type | Description |
|------------|-------------|
| `status` | Progress updates (e.g. "Generating SQL...") |
| `result` | The generated SQL, query results, latency, and attempt count |
| `explanation_token` | Streamed tokens of the natural language explanation |
| `suggestions` | Follow-up question suggestions |
| `error` | Error message if all attempts failed |
| `done` | Stream complete |

### POST `/reindex` — Example

```bash
curl -X POST http://localhost:8000/reindex
```

Response:

```json
{"status": "success", "tables_indexed": 5}
```

---

## Project Structure

```
AskBase/
├── backend/
│   ├── main.py              # FastAPI server, SSE streaming, query pipeline
│   ├── database.py          # PostgreSQL connection, schema extraction, audit logging
│   ├── llm.py               # Ollama LLM integration (SQL generation + explanation)
│   ├── retrieval.py         # ChromaDB schema indexing + semantic retrieval (RAG)
│   ├── seed_db.py           # Sample data seeder (customers, products, orders)
│   ├── seed_db.sql          # Alternative SQL seed script
│   ├── requirements.txt     # Python dependencies
│   ├── Dockerfile           # Backend Docker image
│   └── .env.example         # Environment variable template
├── frontend/
│   ├── src/app/
│   │   ├── page.tsx         # Main chat UI (conversational interface)
│   │   ├── layout.tsx       # Root layout with theme provider
│   │   └── globals.css      # Design system (light + dark mode)
│   ├── src/components/
│   │   ├── theme-provider.tsx
│   │   └── ui/              # shadcn/ui components
│   ├── tailwind.config.ts   # Tailwind configuration
│   ├── package.json         # Node.js dependencies
│   └── Dockerfile           # Frontend Docker image
├── docker-compose.yml       # Full-stack Docker setup (postgres + backend + frontend)
├── init.sql                 # Database init script (read-only user + permissions)
├── start.bat                # Windows start script
├── start.sh                 # macOS/Linux start script
├── .env.example             # Root environment template
├── .gitignore
└── README.md
```

---

## Environment Variables

### `backend/.env`

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_USER` | Database user for queries (should be read-only) | `nl2sql_reader` |
| `POSTGRES_PASSWORD` | Database password | `yourpassword` |
| `POSTGRES_HOST` | Database host | `127.0.0.1` |
| `POSTGRES_PORT` | Database port | `5433` |
| `POSTGRES_DB` | Database name | `yourdatabase` |
| `OLLAMA_BASE_URL` | Ollama API URL | `http://127.0.0.1:11434` |
| `OLLAMA_MODEL` | LLM model to use | `qwen2.5-coder:7b` |

### Root `.env`

| Variable | Description | Default |
|----------|-------------|---------|
| `OLLAMA_MODEL` | LLM model (used by docker-compose) | `qwen2.5-coder:7b` |

---

## Docker (Full Stack)

To run everything in Docker (no manual setup):

```bash
# Make sure Ollama is running on the host machine
ollama serve

# Start all services
docker-compose up -d

# Seed the database (first time only)
docker exec -it $(docker ps -q --filter ancestor=postgres:15) psql -U root -d yourdatabase -f /docker-entrypoint-initdb.d/init.sql
```

Services:
- **Frontend:** http://localhost:3000
- **Backend:** http://localhost:8000
- **PostgreSQL:** localhost:5433

To stop everything:

```bash
docker-compose down
```

To stop and delete all data:

```bash
docker-compose down -v
```

---

## Common Commands Reference

```bash
# ── Start Services ──
docker-compose up -d postgres          # Start only PostgreSQL
uvicorn main:app --reload --port 8000  # Start backend (from backend/ dir)
npm run dev                            # Start frontend (from frontend/ dir)

# ── Database ──
docker exec -it $(docker ps -q --filter ancestor=postgres:15) psql -U root -d yourdatabase
                                        # Connect to PostgreSQL shell

# ── Schema Management ──
curl -X POST http://localhost:8000/reindex   # Re-index schema after adding tables
curl http://localhost:8000/schema            # View current schema as JSON

# ── Health Check ──
curl http://localhost:8000/health       # Check DB + Ollama status

# ── LLM Management ──
ollama list                            # List downloaded models
ollama pull qwen2.5-coder:7b          # Download the default model
ollama pull llama3.1:8b               # Download an alternative model

# ── Git ──
git add -A && git commit -m "message"  # Commit changes
git push                               # Push to GitHub

# ── Stop Services ──
docker-compose down                    # Stop containers
docker-compose down -v                 # Stop + delete data
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| **"Connection refused" on backend start** | Make sure Docker Desktop is running and postgres container is up: `docker ps` |
| **"Model not found" from Ollama** | Run `ollama list` to check. If missing: `ollama pull qwen2.5-coder:7b` |
| **Frontend shows no schema** | Backend must be running on port 8000. Check terminal for errors |
| **"Permission denied" on table** | Grant read access: `GRANT SELECT ON tablename TO nl2sql_reader;` |
| **Schema not updating after adding tables** | Hit the reindex endpoint: `curl -X POST http://localhost:8000/reindex` |
| **Ollama is slow** | Make sure no other heavy processes are running. GPU acceleration helps significantly |
| **Port already in use** | Run `kill_ports.bat` (Windows) or change the port in the start command |

---

## License

This project is for educational purposes.
