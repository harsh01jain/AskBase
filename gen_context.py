# Generates PROJECT_CONTEXT.md - a single self-contained context bundle for the AskBase repo.
# Narrative is authored here; all source code is embedded verbatim from disk so the file
# can be regenerated after any code change:  python gen_context.py
import io, os, sys, datetime

ROOT = r'D:\Downloads\AskBase'
OUT = os.path.join(ROOT, 'PROJECT_CONTEXT.md')

LANG = {
    '.py': 'python', '.ts': 'ts', '.tsx': 'tsx', '.css': 'css', '.sql': 'sql',
    '.json': 'json', '.yml': 'yaml', '.yaml': 'yaml', '.sh': 'bash', '.bat': 'batch',
    '.mjs': 'javascript', '.txt': 'text', '.example': 'ini', '.md': 'markdown',
}

def lang_for(path):
    base = os.path.basename(path)
    if base == 'Dockerfile':
        return 'dockerfile'
    if base.endswith('.env.example') or base == '.env.example':
        return 'ini'
    return LANG.get(os.path.splitext(base)[1], 'text')

def read(rel):
    p = os.path.join(ROOT, rel.replace('/', os.sep))
    if not os.path.exists(p):
        return None
    with io.open(p, encoding='utf-8', errors='replace') as f:
        return f.read().rstrip('\n')

def emit_file(out, rel, note=None):
    body = read(rel)
    if body is None:
        sys.stderr.write('MISSING: %s\n' % rel)
        return
    out.append('### `%s`\n' % rel)
    if note:
        out.append('%s\n' % note)
    fence = '```'
    while fence in body:
        fence += '`'
    out.append('%s%s\n%s\n%s\n' % (fence, lang_for(rel), body, fence))

NARRATIVE = u'''# AskBase - Complete Project Context

> **What this file is.** A single self-contained dump of the entire AskBase project: what it
> does, how it is architected, every design decision and its trade-off, the honest limitations,
> and the **complete verbatim source code** of every file that matters. Paste this into an AI
> assistant (or hand it to a reviewer) and it has everything needed to reason about the project
> without seeing the repository.
>
> Dependency trees (`backend/venv/`, `frontend/node_modules/`), build output (`frontend/.next/`),
> the binary ChromaDB index (`backend/schema_index/`), `package-lock.json` and font/icon binaries
> are deliberately excluded. Live `.env` files are excluded; `.env.example` is included instead
> (the repo's committed credentials are placeholders such as `yourpassword` / `rootpassword`,
> not real secrets - but change them before any real deployment).

---

## 1. Identity and quick facts

| | |
|---|---|
| **Project name** | AskBase (originally **QueryLocal**; the older name still appears in `main.py`'s FastAPI title and the project report) |
| **One line** | A fully local, privacy-first Text-to-SQL web app over PostgreSQL |
| **Author** | Harsh Jain |
| **Programme** | MSc Data Science - NMIMS, 2025 |
| **Domain** | Data Science / NLP / Full-Stack |
| **Type** | Web application (browser, localhost or private LAN) |
| **Repository** | `https://github.com/harsh01jain/AskBase` |
| **LLM** | `qwen2.5-coder:7b` served by Ollama on `:11434` |
| **Embedding model** | `all-MiniLM-L6-v2` (sentence-transformers, 384-dim, ~22M params) |
| **Vector store** | ChromaDB `PersistentClient` -> `backend/schema_index/` |
| **Database** | PostgreSQL 15, Docker, host port **5433**, role `nl2sql_reader` |
| **Backend** | FastAPI + Python 3.11 on `:8000` |
| **Frontend** | Next.js 14 (App Router) + TypeScript on `:3000` |
| **Max retry attempts** | 3 |
| **Retrieval `top_k`** | 5 tables |
| **Row cap** | 1000 (`cur.fetchmany(1000)`) |
| **Statement timeout** | 15 s (role level and session level) |
| **Idle-in-transaction timeout** | 30 s |
| **Suggestions timeout** | 8 s |
| **Seeded demo data** | 1,000 customers - 50 products - 5,000 orders - ~15,000 order items |

### Elevator pitch

> AskBase is a fully local, privacy-first Text-to-SQL web app: you ask a question in plain
> English, a locally-running LLM writes the PostgreSQL query, the app validates it, runs it
> read-only, and streams back the results, a chart and a plain-English explanation - with zero
> data leaving the machine.

---

## 2. The problem it solves

**Business problem.** Analysts raise a ticket, wait for a data engineer, and get back a CSV. That
loop takes hours or days for questions that are 30 seconds of SQL. Worse, exploration quietly
dies - nobody raises a ticket just to check a hunch. Self-service NL-to-SQL removes the queue.

**Why not a cloud LLM?** Cloud NL-to-SQL (OpenAI, BigQuery NL mode) sends the **schema** and often
**sample data** to a third-party API. For BFSI / healthcare / government that is a data-residency
violation (GDPR Art. 25, India's DPDP Act 2023), not merely a preference. The query text itself
leaks intent ("churn risk", "salary band", "patient cohort"). Per-token billing also scales with
curiosity - the tool costs more the more it is used - and there is no offline path.

**Positioning.** The right comparison is not "is it as accurate as GPT-4". It is: this is an
on-prem NL-to-SQL tool with a real web UI, semantic schema retrieval and hard SQL guardrails that
a compliance officer would sign off on. It is **private by construction, not by configuration** -
there is no cloud code path in the system to misconfigure.

**Why a web app, not a desktop/Streamlit app.** One GPU server serves the whole analyst team;
updates deploy once; no per-laptop install of Python, Ollama and CUDA. Privacy is preserved
because it is hosted on the client's own machine or private network, not the public internet.

---

## 3. System architecture

```
+--------------------------------------------------------------------------+
|                          Browser (localhost:3000)                        |
|  Next.js 14 App Router - TypeScript - Tailwind - Recharts - next-themes   |
|  chat UI, SQL block, results table, bar chart, follow-up chips,           |
|  Web Speech API voice input, dark/light theme                            |
+----------------------------+---------------------------------------------+
                             |  fetch() + ReadableStream reader
                             |  POST /query  ->  text/event-stream (SSE)
                             v
+--------------------------------------------------------------------------+
|                    FastAPI backend (localhost:8000)                      |
|                              main.py                                     |
|   +---------------+  +--------------+  +---------------+  +-----------+  |
|   | retrieval.py  |->|   llm.py     |->| validate_sql  |->|database.py|  |
|   | ChromaDB RAG  |  | Ollama HTTP  |  |  sqlglot AST  |  | psycopg2  |  |
|   +---------------+  +--------------+  +---------------+  +-----------+  |
|                        ^---- self-correction loop (max 3) ----+          |
+-------+------------------------+---------------------------+------------+
        |                        |                           |
        v                        v                           v
+----------------+     +--------------------+     +---------------------+
| ChromaDB       |     | Ollama             |     | PostgreSQL 15       |
| ./schema_index |     | :11434             |     | :5433 (Docker)      |
| all-MiniLM-L6  |     | qwen2.5-coder:7b   |     | role: nl2sql_reader |
| (on disk)      |     | (on host GPU/CPU)  |     | SELECT-only         |
+----------------+     +--------------------+     +---------------------+
```

**Three "brains" the backend talks to:**

- **ChromaDB** - vector store of table descriptions; answers *"which tables matter for this question?"*
- **Ollama** - local LLM server; answers *"what SQL answers this question?"*
- **PostgreSQL** - the actual data; answers the question.

---

## 4. Tech stack and why each piece was chosen

| Layer | Technology | Rationale |
|---|---|---|
| Frontend | **Next.js 14 (App Router) + TypeScript** | Type safety across the API boundary; App Router for a single-page chat shell; standard Node deployment. |
| Styling | **Tailwind CSS + CSS variables + shadcn/ui** | Design tokens in `globals.css` drive light/dark theming with no duplicated styles. |
| Charts | **Recharts** | Declarative React charting; the app infers x/y axes from result columns automatically. |
| Theme | **next-themes** | `attribute="class"`, `defaultTheme="dark"`, `enableSystem` - respects OS preference, persists choice. |
| Backend | **FastAPI + Python 3.11** | Native async, `StreamingResponse` for SSE, Pydantic request validation, auto OpenAPI docs. |
| Streaming | **Server-Sent Events (SSE)** | One-way server->client streaming; simpler than WebSockets, plain HTTP, ideal for token streaming. |
| LLM serving | **Ollama** running `qwen2.5-coder:7b` | Native Windows installer (no WSL2/CUDA toolkit), simple `/api/generate` REST API, code-specialised model. |
| Embeddings | **sentence-transformers `all-MiniLM-L6-v2`** | 384-dim, ~22M params, runs on CPU in milliseconds, strong quality-per-cost for short schema strings. |
| Vector DB | **ChromaDB PersistentClient** | Embedded (no server process), persists to `./schema_index`, telemetry disabled, bundles the embedding function so index-time and query-time embeddings cannot drift. |
| SQL safety | **sqlglot** | A real SQL **parser** producing an AST - you check the statement *type*, not a regex on a string. |
| Database | **PostgreSQL 15** | `information_schema` for reflection, role-level privileges, `statement_timeout`. |
| DB driver | **psycopg2** with `RealDictCursor` | Returns rows as dicts -> serialises straight to JSON for the frontend. |
| HTTP clients | **requests** (sync) + **httpx** (async streaming) | `requests` for the blocking SQL-generation call; `httpx.AsyncClient.stream` for token-by-token explanation. |
| Packaging | **Docker Compose** | postgres + backend + frontend on one private bridge network; Ollama stays on the host via `host.docker.internal`. |

---

## 5. The request lifecycle (the core of the project)

Source: `backend/main.py` -> `process_query()`. Everything below happens inside an **async
generator**, so each `yield` flushes to the browser immediately.

### Stage 0 - Request arrives

```python
class QueryRequest(BaseModel):
    question: str
    history: list[dict] = []     # prior {question, sql} pairs for conversational context
```

FastAPI returns `StreamingResponse(event_stream(), media_type="text/event-stream")`.

### Stage 1 - Schema retrieval (RAG)

`context = retrieve_context(question, top_k=5)`

- The question text is embedded by `all-MiniLM-L6-v2`.
- ChromaDB does an approximate nearest-neighbour search over stored table-description embeddings.
- Returns the top 5 table description strings, e.g.
  `"Table: orders. Columns: order_id (integer), customer_id (integer), order_date (date), total_amount (numeric), status (character varying)"`

**Why RAG here?** Naively pasting a 100-table schema into the prompt blows the context window,
costs latency, and *hurts* accuracy (the model gets distracted by irrelevant tables). Retrieval
keeps the prompt small and relevant, and means the design scales to large databases unchanged.

### Stage 2 - SQL generation (attempt N)

`sql = generate_sql(question, context, history=req.history, error_context=error_msg)`

The prompt is assembled in `llm.py` from four blocks:

1. **Role + hard rules** - "You are a PostgreSQL expert... only use listed tables/columns, don't
   invent names, map concepts to columns, always use `ILIKE` for string comparisons."
2. **Schema context** - the retrieved table descriptions.
3. **Chat history** - the last 3 `(question, sql)` pairs, so follow-ups like "now only for 2023" work.
4. **Error context** - on retries, the verbatim Postgres error from the previous attempt.

Then: `"Respond ONLY with the raw SQL query, no markdown formatting, no explanation."` A
post-processing step strips ```` ```sql ```` fences anyway, because models ignore that
instruction often enough to matter. The call is `POST {OLLAMA_BASE_URL}/api/generate` with
`stream: False` and a 30 s timeout.

### Stage 3 - Validation (the safety gate)

```python
def validate_sql(sql: str) -> bool:
    parsed = sqlglot.parse(sql, read="postgres")   # -> list of AST root nodes
    if not parsed: return False
    for node in parsed:
        if not isinstance(node, sqlglot.exp.Select):
            return False
    return True
```

Three things this buys:

- **Type check, not string check.** `INSERT`/`UPDATE`/`DELETE`/`DROP`/`ALTER` parse into different
  AST classes and are rejected.
- **Multi-statement injection defence.** `sqlglot.parse` returns a *list*; `SELECT 1; DROP TABLE
  customers;` produces `[Select, Drop]` -> the loop rejects it.
- **Syntax check for free.** Malformed SQL throws during parse -> rejected before touching the database.

If validation fails, the error string becomes `error_context` and the loop retries.

### Stage 4 - Execution

`result = execute_query(sql)` in `database.py`:

- Opens a fresh connection as `nl2sql_reader` (`connect_timeout=5`).
- Sets `statement_timeout = 15000` ms and `idle_in_transaction_session_timeout = 30000` ms per session.
- Executes with a `RealDictCursor`, then `cur.fetchmany(1000)` - a 1000-row cap on what is returned.
- Returns `{"columns": [...], "rows": [...]}` on success, or `{"error": "<postgres message>"}` on failure.

### Stage 5 - Self-correction loop

```python
while attempt < max_attempts:      # max_attempts = 3
    attempt += 1
    sql = generate_sql(..., error_context=error_msg)
    if not validate_sql(sql):  error_msg = "Validation Error: ..."; continue
    result = execute_query(sql)
    if "error" in result:      error_msg = result["error"];         continue
    success = True; break
```

**Why this matters.** A Postgres error message is *extremely* informative context -
`column "revenue" does not exist` tells the model exactly what to fix. This retry loop is the
single biggest accuracy lever in the project: it lets a 7B local model recover from mistakes a
7B model reliably makes, narrowing the gap to a much larger cloud model. Capped at 3 to bound
worst-case latency - beyond that, models tend to loop on the same mistake.

### Stage 6 - Audit logging

```python
latency_ms = int((time.time() - start_time) * 1000)
insert_audit_log(question, sql, attempt, latency_ms, "Success" | "Failed")
```

Every request - success or failure - is written to a `query_audit` table. That gives an audit
trail for compliance **and** a metrics table for regression tracking (retry rate, P95 latency per
model version).

### Stage 7 - Streaming the response

The SSE stream emits typed JSON events, each framed as `data: {...}\\n\\n`:

| `type` | Payload | Purpose |
|---|---|---|
| `status` | `message` | Progress text ("Generating SQL (Attempt 2)...") |
| `result` | `sql`, `results`, `attempts`, `latency_ms` | The main payload |
| `explanation_token` | `token` | One token of the plain-English explanation |
| `suggestions` | `data: string[]` | 3 follow-up questions |
| `error` | `sql`, `error`, `attempts` | All attempts failed |
| `done` | - | Stream complete |

**Concurrency detail:** suggestions are kicked off as a background task *before* the explanation
starts streaming, then awaited with a timeout:

```python
suggestions_task = asyncio.create_task(generate_suggestions(question, sql))
async for token in stream_explanation(question, sql):
    yield explanation_token
suggestions = await asyncio.wait_for(suggestions_task, timeout=8.0)
```

So two LLM calls overlap instead of running back-to-back, and a slow suggestions call cannot hang
the response.

**Serialization detail:** results contain `datetime.date` and `Decimal` values that `json.dumps`
cannot handle. `fastapi.encoders.jsonable_encoder` is applied to the payload first (dates -> ISO
strings, Decimals -> numbers).

---

## 6. Frontend behaviour worth knowing

A single main component: `frontend/src/app/page.tsx` (a `"use client"` component).

### State model

```
messages       // full chat transcript: {role, content, sql, results, explanation, attempts, latency, loading, error}
chatHistory    // compact [{question, sql}] sent back to the API for conversational context
suggestions    // 3 follow-up chips; seeded with defaults, replaced by LLM output
schema         // table list from GET /schema, rendered in the sidebar
history        // GET /history audit rows, shown in a modal
activeTab      // "table" | "chart"
```

### SSE consumption is hand-rolled, and there is a reason

The browser's built-in `EventSource` API **only supports GET**. This endpoint is a `POST` with a
JSON body, so the code uses `fetch` + the streaming `ReadableStream` reader and parses the SSE
framing manually. Two subtleties:

- **The buffer exists because TCP chunks don't align with SSE messages.** One `read()` may deliver
  half an event or three events; you must accumulate and split on the `\\n\\n` delimiter.
- **`decoder.decode(value, {stream: true})`** keeps multi-byte UTF-8 characters intact across chunk
  boundaries.

Each parsed event immutably updates the **last** message in `messages`
(`const last = {...updated[len-1]}`), so React re-renders correctly - mutating in place would not
trigger an update.

### Auto-charting heuristic

The first numeric column becomes the Y axis, the first non-numeric column becomes the X axis;
falls back to `columns[0]`/`columns[1]`, and shows "Not enough numeric data to visualize" if no
pair is found. Simple, but it covers the dominant shape of analytics results: one label column
plus one measure column.

### Other UI features

- **Voice input** - Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`) with
  `interimResults: true`. Feature-detected, with an alert if unsupported.
- **Theming** - `next-themes` toggles a `.dark` class; all colors are CSS variables in
  `globals.css`, so one class flip re-themes the app.
- **Hydration safety** - a `mounted` flag gates theme-dependent icons; `suppressHydrationWarning`
  on `<html>`. Without this, server and client render different icons and React warns.
- **Latency and attempt badges** on the SQL block - surfacing `latency_ms` and `attempts` makes the
  retry loop visible to the user instead of hidden magic.
- **Copy SQL**, **New chat**, **History modal** (click a past question to re-run it), **Enter to
  send / Shift+Enter for newline**.
- **Trust disclaimer** under the input: "AskBase generates SQL from natural language. Always verify
  results." A deliberate design decision - see the trade-offs section.

---

## 7. Data model and sample dataset

```
customers                       products
---------                       --------
customer_id  PK  SERIAL         product_id  PK  SERIAL
name             VARCHAR(100)   name            VARCHAR(100)
email            VARCHAR(100)   category        VARCHAR(50)
segment          VARCHAR(50)    price           DECIMAL(10,2)
signup_date      DATE                  ^
     |                                 | N..1
     | 1..N                            |
     v                                 |
orders                          order_items
------                          -----------
order_id     PK  SERIAL         order_item_id PK SERIAL
customer_id  FK -> customers    order_id      FK -> orders
order_date       DATE           product_id    FK -> products
total_amount     DECIMAL(10,2)  quantity         INT
status           VARCHAR(20)    unit_price       DECIMAL(10,2)
     |                                 ^
     +---------------- 1..N -----------+

query_audit  (created by the app, written via the admin role)
-----------
id PK - question - generated_sql - attempts - latency_ms - status - timestamp
```

Segments: `Enterprise`, `SMB`, `Startup`, `Mid-Market`. Categories: `Software`, `Hardware`,
`Services`, `Consulting`. Date range: 2021-01-01 -> 2024-01-01.

This is a deliberately classic e-commerce schema: it exercises single-table filters, joins,
`GROUP BY` aggregation and date arithmetic - the difficulty tiers you would evaluate a text-to-SQL
system on.

---

## 8. Security model - defense in depth

The core claim: **even if the LLM is fully compromised or hallucinates a `DROP TABLE`, nothing bad
happens.** Four independent layers, each of which alone would be insufficient:

| # | Layer | Mechanism | Stops |
|---|---|---|---|
| 1 | **Application validation** | `sqlglot` parses to an AST; every root node must be `exp.Select` | DDL/DML, multi-statement injection, malformed SQL |
| 2 | **Database privileges** | `nl2sql_reader` has only `CONNECT`, `USAGE`, `SELECT`; `ALTER DEFAULT PRIVILEGES` extends SELECT to future tables | Any write, even if layer 1 were bypassed |
| 3 | **Resource limits** | `statement_timeout = 15s`, `idle_in_transaction_session_timeout = 30s`, set at both role level (`init.sql`) and per session | Runaway cartesian joins, connection exhaustion |
| 4 | **Result cap** | `cur.fetchmany(1000)` | Dumping a million-row table into the browser |

**Privacy layers:**

- Ollama inference runs entirely on `localhost:11434` - no API key, no outbound call.
- sentence-transformers downloads the embedding model once, then runs CPU-local forever.
- ChromaDB is an embedded persistent client writing to local disk, with `anonymized_telemetry=False`.
- After first-run downloads, the whole system works **fully offline**.

**Least privilege in one sentence:** the role that executes untrusted (LLM-generated) SQL is a
different, strictly weaker role than the one that writes the audit log.

**Weaknesses to volunteer:** CORS is `["*"]`, there is no authentication layer, and admin DB
credentials live in environment variables. All are acceptable for a localhost / private-network
deployment, and all are the first things to fix before a multi-user rollout.

---

## 9. API reference

| Method | Path | Returns |
|---|---|---|
| `GET` | `/health` | `{"database": "ok"|"error", "ollama": "ok"|"error"}` |
| `GET` | `/schema` | `[{"table": "...", "description": "Table: ... Columns: ..."}]` |
| `GET` | `/history` | Last 50 `query_audit` rows, newest first |
| `POST` | `/reindex` | `{"status": "success", "tables_indexed": N}` |
| `POST` | `/query` | `text/event-stream` - typed SSE events (see section 5, Stage 7) |

Request body for `/query`:

```json
{ "question": "Show me the top 5 customers by revenue",
  "history": [{"question": "...", "sql": "..."}] }
```

---

## 10. Setup and run

**Prerequisites:** Node.js v18+, Python 3.10+, Docker Desktop, Ollama, Git.

```bash
# 1. Pull the model (~4GB)
ollama pull qwen2.5-coder:7b

# 2. Start the database
docker-compose up -d postgres            # postgres:15 on host port 5433

# 3. Backend
cd backend
python -m venv venv
venv\\Scripts\\activate                    # Windows;  source venv/bin/activate on macOS/Linux
pip install -r requirements.txt
copy .env.example .env                   # cp on macOS/Linux
python seed_db.py                        # 1000 customers, 50 products, 5000 orders
uvicorn main:app --reload --port 8000

# 4. Frontend (new terminal)
cd frontend
npm install
npm run dev                              # http://localhost:3000
```

**Connecting to your own PostgreSQL:** edit `backend/.env` with your credentials and restart the
backend. It reads all tables from the `public` schema, indexes them into ChromaDB and shows them
in the sidebar. Then re-index: `curl -X POST http://localhost:8000/reindex`. Always connect with a
**read-only** user.

**Adding tables:** create them in Postgres, `GRANT SELECT ON tablename TO nl2sql_reader;`, then
`POST /reindex`.

**Full Docker stack:** `docker-compose up -d` (Ollama must be running on the host - the backend
reaches it via `host.docker.internal`). `docker-compose down -v` stops and deletes all data.

**Convenience scripts:** `start.bat` / `start.sh` bring up the whole stack;
`kill_ports.bat` / `kill_ports.py` free ports 3000/8000.

### Environment variables

`backend/.env`: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT`,
`POSTGRES_DB`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL` (plus `POSTGRES_ADMIN_USER` /
`POSTGRES_ADMIN_PASSWORD`, read in `database.py` for the audit-log connection).
Root `.env`: `OLLAMA_MODEL` for docker-compose interpolation.

---

## 11. Key design decisions and trade-offs

**1. RAG over the schema instead of dumping the whole schema.**
*Trade-off:* retrieval can *miss* a needed table (a recall failure), producing a wrong query.
*Justification:* prompt size stays constant as the database grows, latency stays low, and accuracy
improves because irrelevant tables don't distract the model. `top_k=5` is the tuning knob.

**2. sqlglot AST validation instead of regex blocklists.**
A regex like `/drop|delete/i` is trivially bypassed (comments, casing, nested statements) and
produces false positives (a column literally named "deleted"). Parsing to an AST and asserting the
node type is categorical, not heuristic.

**3. Self-correction loop capped at 3.**
*Trade-off:* worst case is 3x the latency. *Justification:* each attempt carries the exact DB
error, so success probability rises steeply on attempt 2; beyond 3, models tend to loop on the
same mistake, so more retries buy latency but not accuracy.

**4. SSE instead of WebSockets.**
The data flow is strictly server->client during a query. SSE is plain HTTP (no upgrade handshake,
no extra infrastructure), auto-reconnects, and is trivially proxied. WebSockets would be
over-engineering.

**5. Non-streaming SQL generation, streaming explanation.**
You cannot validate a half-written SQL statement, so SQL is generated in full. The *explanation*
has no correctness gate, so streaming it token-by-token is pure UX win - perceived latency drops
even though total time is unchanged.

**6. A 7B model, not 32B, as the default.**
Fits in 8 GB VRAM and runs on CPU. The RAG + retry loop is explicitly the compensation for the
smaller model. The model is one env var (`OLLAMA_MODEL`), so upgrading to `:14b` or `:32b` on
better hardware is a one-line change.

**7. Always show the generated SQL.**
The dangerous failure mode in text-to-SQL is not an error - it is a query that runs cleanly and
answers a *subtly different question*. No validator catches that. Showing the SQL plus a
plain-English explanation makes the system auditable by the human, which is also why the
disclaimer line exists.

**8. Two database roles.**
Audit logging needs INSERT; the query path must never have it. Splitting identities keeps the
least-privilege property intact rather than weakening the reader role for convenience.

**9. Web app, not a desktop/Streamlit app.**
One GPU server serves the whole analyst team; updates deploy once; no per-laptop install. Privacy
is preserved because it is hosted on the private network, not the public internet.

**10. Ollama on the host, not containerised.**
GPU passthrough into a container needs the NVIDIA Container Toolkit and is fragile on Windows; the
host-installed Ollama already has GPU acceleration and its model cache. `host.docker.internal`
plus an `extra_hosts: host-gateway` entry bridges the two cleanly.

---

## 12. Challenges faced

### Technical

| Challenge | Resolution |
|---|---|
| **A small model invents column names** - a 7B model happily writes `SUM(revenue)` against a table with no such column. | Three fixes stacked: retrieval so only real table descriptions enter the prompt, explicit "never invent names" rules, and the error-feedback retry loop. |
| **`EventSource` cannot POST** - the browser's built-in SSE client is GET-only, but `/query` needs a JSON body. | Read the `fetch` `ReadableStream` directly and parse the SSE framing by hand, buffering across reads because TCP chunk boundaries do not align with message boundaries. |
| **Postgres types JSON cannot encode** - results contain `Decimal` and `datetime.date`; `json.dumps` refuses both. | Run every payload through `fastapi.encoders.jsonable_encoder` before serialising. |
| **GPU passthrough into Docker** - containerising Ollama on Windows needs the NVIDIA Container Toolkit and breaks easily. | Keep Ollama on the host with its GPU acceleration and model cache; the containerised backend reaches it through `host.docker.internal` and a host-gateway entry. |

### Non-technical

| Challenge | Resolution |
|---|---|
| **Hardware set the ceiling** - an 8 GB VRAM budget rules out the models that would make this easy. | Chose a code-specialised 7B model that also degrades gracefully to CPU, and treated retrieval plus retries as the compensation for its size. |
| **The plan drifted from the build** - the project report was written at planning stage and promised things the shipped code does not do. | Rather than quietly dropping them, every divergence is tracked in the report-versus-code table below. |
| **Earning an analyst's trust** - a confident black box is worse than no tool; a wrong number nobody can check ends up in a board deck. | Made the SQL, retry count and latency permanently visible, added a streamed explanation, and put a verify-your-results disclaimer under the input box. |
| **No evaluation budget** - measuring text-to-SQL properly needs a hand-built gold set. | Accepted the gap honestly instead of quoting an unmeasured accuracy figure, and built the audit log first so the data for a future evaluation is already being collected. |

---

## 13. Known gaps: where the code differs from the project report

The original report (`project_docs.txt`) was written at planning stage and describes some things
the shipped code does not do:

| Report claims | Actual code | Note |
|---|---|---|
| "1000-row `LIMIT` injected into the SQL" | `cur.fetchmany(1000)` - capped **client-side** | Postgres still computes the full result set, and psycopg2's default cursor buffers it. Real fix: inject `LIMIT` into the AST with sqlglot, or use a server-side named cursor. |
| Prompts stored in `/prompts/` templates; model read from `config.yaml` | Prompts are f-strings in `llm.py`; model comes from an env var | The env var still gives model hot-swap without code changes. |
| Startup health gate returns 503 if Ollama is down | `/health` exists, but there is no startup gate | |
| Backend auto-indexes schema on startup (README) | No startup event calls `index_schema()`; you must `POST /reindex` | Worth fixing - it is a two-line `@app.on_event("startup")`. |
| Editable SQL field on final failure | The error and last SQL are displayed, not editable | |
| 4 follow-up suggestions | 3 | |
| Schema panel highlights tables used in the current query | Sidebar lists tables and expands to show columns | |
| SQL streams token-by-token to the UI | Only the *explanation* streams; SQL arrives complete | Intentional - see trade-off 5. |
| Ollama runs as a Docker service with GPU passthrough | Ollama runs on the host, reached via `host.docker.internal` | Intentional - see trade-off 10. |
| Gold-set regression suite / evaluation harness | Not implemented | The biggest genuine gap. |

---

## 14. Limitations of the current code

**Functional**

- `validate_sql` accepts only `exp.Select` root nodes, so a `UNION` query (which parses as
  `exp.Union`) is rejected even though it is read-only. CTEs (`WITH ... SELECT`) are fine, because
  sqlglot attaches them to the Select node.
- The 1000-row cap is client-side - Postgres still computes the full result set first.
- Schema indexing is not triggered on startup; a new table needs a manual `POST /reindex`.
- The charting heuristic takes the first numeric column as the measure - fine for one label plus
  one measure, wrong for anything richer.
- Accuracy is unquantified - there is no gold-set evaluation harness yet.

**Engineering / production-readiness**

- `generate_sql` uses a **blocking `requests.post` inside an async endpoint** - it blocks the event
  loop for the duration of inference, so concurrent users serialise. Fix: `httpx.AsyncClient` or
  `run_in_threadpool`.
- Each query opens a **new database connection** - no pooling (`psycopg2.pool` or PgBouncer would fix it).
- `CORS allow_origins=["*"]` - fine on localhost, wrong for a network deployment.
- No authentication/authorisation layer, no per-user row-level security.
- No automated tests; the `test_*.py` files are manual smoke scripts.
- The frontend hardcodes `http://localhost:8000` even though compose passes `NEXT_PUBLIC_API_URL`.
- Reindexing deletes and recreates the whole Chroma collection rather than upserting deltas.
- Deployment scope is localhost or a trusted private network, never the public internet.

**The hardest failure mode** is not an error at all: a query that executes successfully but answers
a subtly different question - wrong JOIN condition, missing WHERE filter, aggregation on the wrong
column. No automated layer catches it. That is why the SQL and its plain-English explanation are
always shown, and why the disclaimer sits under the input box.

---

## 15. Future scope, in priority order

1. **Evaluation harness** - 30-50 gold `(question, SQL)` pairs; compare *executed result sets* as
   sorted DataFrames, not SQL strings (many correct queries are textually different). Track
   execution accuracy, retry-rate distribution, and P95 latency; gate model/prompt changes on a
   >5% regression.
2. **Real `LIMIT` injection** - rewrite the AST with sqlglot to append or clamp a `LIMIT`, instead
   of capping client-side.
3. **Async LLM calls + connection pooling** - remove the blocking `requests` call; add `psycopg2.pool`.
4. **Auth + tightened CORS** - Next.js middleware with JWT, an origin allowlist, per-user audit attribution.
5. **Auto-reindex on startup, plus schema-change detection.**
6. **Richer schema context** - foreign-key relationships, column comments, and a few sample values
   per column. FK knowledge is the single biggest driver of correct JOINs.
7. **Few-shot examples in the prompt** - retrieve similar previously-successful `(question, SQL)`
   pairs from the audit table and include them. That turns the audit log into a self-improving
   example store.
8. **Result caching** - hash (question + schema version) -> cached SQL, to skip inference on repeat questions.
9. **Scale the model and the store** - `qwen2.5-coder:32b` is a one-line env change on better
   hardware; pgvector would move embeddings into Postgres itself.

---

## 16. Glossary

- **Text-to-SQL / NL2SQL** - translating a natural-language question into an executable SQL query.
- **RAG (Retrieval-Augmented Generation)** - retrieve relevant context from a knowledge store and
  inject it into the prompt, instead of relying on the model's parameters. Here the "knowledge" is
  the database schema.
- **Embedding** - a dense vector representation of text where semantic similarity is geometric closeness.
- **Vector database** - stores embeddings and answers approximate nearest-neighbour queries.
- **`all-MiniLM-L6-v2`** - a small sentence-transformer producing 384-dim embeddings; fast on CPU.
- **AST (Abstract Syntax Tree)** - the parsed tree structure of code. sqlglot produces one; the
  validator checks the root node's *type*.
- **SSE (Server-Sent Events)** - HTTP streaming of `data: ...\\n\\n` frames, server->client only.
- **`statement_timeout`** - a Postgres setting that aborts any query exceeding a duration.
- **Least privilege** - grant exactly the permissions needed, nothing more.
- **Self-correction / error-feedback loop** - feeding a failed execution's error back into the
  model to regenerate.
- **Ollama** - a local LLM server exposing a REST API (`/api/generate`) over quantised GGUF models.
- **Qwen2.5-Coder** - Alibaba's code-specialised LLM family; strong at SQL for its parameter count.
- **Quantisation (Q4)** - compressing model weights to 4 bits to fit in less VRAM, trading a little
  accuracy for size and speed.
- **`information_schema`** - the SQL-standard set of views describing a database's own tables and columns.
- **Idempotent seeding** - `TRUNCATE ... RESTART IDENTITY CASCADE`, so re-running the seeder gives
  the same state.
- **Hydration mismatch** - a React error when server-rendered HTML differs from the client's first
  render; handled here with a `mounted` flag and `suppressHydrationWarning`.

---

## 17. Repository structure

```
AskBase/
|-- backend/
|   |-- main.py              # FastAPI server, SSE streaming, query pipeline, validate_sql
|   |-- database.py          # PostgreSQL connection, schema extraction, audit logging
|   |-- llm.py               # Ollama integration (SQL generation, explanation, suggestions)
|   |-- retrieval.py         # ChromaDB schema indexing + semantic retrieval (RAG)
|   |-- seed_db.py           # Sample data seeder
|   |-- seed_db.sql          # Alternative SQL seed script
|   |-- kill_ports.py        # Frees ports 3000/8000
|   |-- test_*.py            # Manual smoke scripts (not a test suite)
|   |-- requirements.txt
|   |-- Dockerfile
|   |-- .env.example
|   `-- schema_index/        # ChromaDB persistent store (binary, gitignored)
|-- frontend/
|   |-- src/app/
|   |   |-- page.tsx         # Main chat UI - the entire client application
|   |   |-- layout.tsx       # Root layout with theme provider
|   |   `-- globals.css      # Design system (light + dark mode CSS variables)
|   |-- src/components/
|   |   |-- theme-provider.tsx
|   |   `-- ui/              # shadcn/ui components
|   |-- src/lib/utils.ts
|   |-- tailwind.config.ts
|   |-- package.json
|   `-- Dockerfile
|-- docker-compose.yml       # Full-stack setup (postgres + backend + frontend)
|-- init.sql                 # Read-only role + permissions + role-level timeouts
|-- start.bat / start.sh     # Start the whole stack
|-- kill_ports.bat
|-- .env.example
|-- README.md                # Setup, DB connection, table management, API reference
|-- PROJECT_EXPLAINER.md     # Long-form study/interview document
|-- PROJECT_CONTEXT.md       # This file
`-- project_docs.txt         # The original planning-stage project report
```

---

# 18. Complete source code

Everything below is verbatim from the repository.

## 18.1 Infrastructure and configuration
'''


def main():
    out = [NARRATIVE]

    out.append('\n')
    emit_file(out, 'docker-compose.yml',
              'Three services on a private bridge network. Postgres publishes host port **5433** to avoid '
              'clashing with a locally installed Postgres. The backend reaches Ollama on the host via '
              '`host.docker.internal` + `extra_hosts: host-gateway`.')
    emit_file(out, 'init.sql',
              'Runs once on first Postgres container start. `ALTER DEFAULT PRIVILEGES` is the important '
              'line: without it, every newly created table would be invisible to the reader role. '
              'Role-level `SET` means the timeouts survive application restarts and misconfiguration.')
    emit_file(out, '.env.example', 'Root env - used for docker-compose interpolation.')
    emit_file(out, 'start.sh')
    emit_file(out, 'start.bat')
    emit_file(out, 'kill_ports.bat')

    out.append('\n## 18.2 Backend (FastAPI + Python)\n')
    emit_file(out, 'backend/.env.example')
    emit_file(out, 'backend/requirements.txt')
    emit_file(out, 'backend/Dockerfile')
    emit_file(out, 'backend/main.py',
              '**The core of the project.** FastAPI app, `validate_sql` AST gate, and `process_query` - '
              'the async generator implementing retrieve -> generate -> validate -> execute -> '
              'self-correct -> stream.')
    emit_file(out, 'backend/llm.py',
              'All three Ollama calls: blocking SQL generation, streamed explanation, and JSON-mode '
              'follow-up suggestions. Prompts are f-strings here, not template files.')
    emit_file(out, 'backend/retrieval.py',
              'ChromaDB indexing and retrieval. Note `index_schema` deletes and recreates the whole '
              'collection rather than upserting deltas.')
    emit_file(out, 'backend/database.py',
              'Two connection identities: `get_db_connection()` (the read-only `nl2sql_reader` role, used '
              'for LLM-generated SQL) and `get_admin_connection()` (writes the audit table). '
              '`init_audit_table()` runs at import time.')
    emit_file(out, 'backend/seed_db.py', 'Idempotent seeder - `TRUNCATE ... RESTART IDENTITY CASCADE` then regenerate.')
    emit_file(out, 'backend/seed_db.sql', 'Pure-SQL alternative to the Python seeder.')
    emit_file(out, 'backend/kill_ports.py')
    emit_file(out, 'backend/check_users.sql', 'One-off psql admin snippet.')
    emit_file(out, 'backend/reset_passwords.sql',
              'One-off psql admin snippet. These are the repo\'s placeholder credentials - change them '
              'before any real deployment.')

    out.append('\n### Manual smoke scripts\n')
    out.append('These are *not* an automated test suite - they are throwaway scripts used during '
               'development. Their existence is a known gap, not a testing strategy.\n')
    for f in ['backend/test_api.py', 'backend/test_conn.py', 'backend/test_encoder.py',
              'backend/test_history.py', 'backend/test_openapi.py']:
        emit_file(out, f)

    out.append('\n## 18.3 Frontend (Next.js 14 + TypeScript)\n')
    emit_file(out, 'frontend/package.json')
    emit_file(out, 'frontend/next.config.mjs')
    emit_file(out, 'frontend/tsconfig.json')
    emit_file(out, 'frontend/tailwind.config.ts')
    emit_file(out, 'frontend/components.json')
    emit_file(out, 'frontend/Dockerfile')
    emit_file(out, 'frontend/src/app/layout.tsx')
    emit_file(out, 'frontend/src/app/globals.css',
              'The whole design system: CSS variables for light and dark, flipped by a single `.dark` class.')
    emit_file(out, 'frontend/src/app/page.tsx',
              '**The entire client application in one `"use client"` component** - chat state, the '
              'hand-rolled SSE parser, the results table, the auto-charting heuristic, voice input, the '
              'schema sidebar and the history modal.')
    emit_file(out, 'frontend/src/components/theme-provider.tsx')
    emit_file(out, 'frontend/src/lib/utils.ts')

    out.append('\n### shadcn/ui components\n')
    for f in ['frontend/src/components/ui/badge.tsx', 'frontend/src/components/ui/button.tsx',
              'frontend/src/components/ui/card.tsx', 'frontend/src/components/ui/input.tsx',
              'frontend/src/components/ui/scroll-area.tsx', 'frontend/src/components/ui/table.tsx']:
        emit_file(out, f)

    out.append('\n---\n')
    out.append('*Generated %s from the AskBase repository. Regenerate after code changes so this '
               'file never drifts from the source.*\n' % datetime.date.today().isoformat())

    text = '\n'.join(out)
    with io.open(OUT, 'w', encoding='utf-8') as f:
        f.write(text)
    print('WROTE %s  (%d lines, %.1f KB)' % (OUT, text.count('\n') + 1, len(text.encode('utf-8')) / 1024.0))


if __name__ == '__main__':
    main()
