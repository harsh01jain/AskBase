# AskBase - Complete Project Context

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

The SSE stream emits typed JSON events, each framed as `data: {...}\n\n`:

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
  half an event or three events; you must accumulate and split on the `\n\n` delimiter.
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
venv\Scripts\activate                    # Windows;  source venv/bin/activate on macOS/Linux
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
- **SSE (Server-Sent Events)** - HTTP streaming of `data: ...\n\n` frames, server->client only.
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



### `docker-compose.yml`

Three services on a private bridge network. Postgres publishes host port **5433** to avoid clashing with a locally installed Postgres. The backend reaches Ollama on the host via `host.docker.internal` + `extra_hosts: host-gateway`.

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: root
      POSTGRES_PASSWORD: rootpassword
      POSTGRES_DB: yourdatabase
    ports:
      - "5433:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    restart: unless-stopped
    networks:
      - querylocal-net

  backend:
    build:
      context: ./backend
    ports:
      - "8000:8000"
    environment:
      - POSTGRES_USER=nl2sql_reader
      - POSTGRES_PASSWORD=readonly_password
      - POSTGRES_HOST=postgres
      - POSTGRES_PORT=5432
      - POSTGRES_DB=yourdatabase
      - POSTGRES_ADMIN_USER=root
      - POSTGRES_ADMIN_PASSWORD=rootpassword
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
      - OLLAMA_MODEL=${OLLAMA_MODEL:-qwen2.5-coder:7b}
    depends_on:
      - postgres
    extra_hosts:
      - "host.docker.internal:host-gateway"
    networks:
      - querylocal-net

  frontend:
    build:
      context: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on:
      - backend
    networks:
      - querylocal-net

volumes:
  pgdata:

networks:
  querylocal-net:
    driver: bridge
```

### `init.sql`

Runs once on first Postgres container start. `ALTER DEFAULT PRIVILEGES` is the important line: without it, every newly created table would be invisible to the reader role. Role-level `SET` means the timeouts survive application restarts and misconfiguration.

```sql
-- Create the read-only role
CREATE ROLE nl2sql_reader WITH LOGIN PASSWORD 'yourpassword';
GRANT CONNECT ON DATABASE yourdatabase TO nl2sql_reader;
GRANT USAGE ON SCHEMA public TO nl2sql_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO nl2sql_reader;

-- Ensure future tables also get SELECT grants
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO nl2sql_reader;

-- Apply timeouts
ALTER ROLE nl2sql_reader SET statement_timeout = '15s';
ALTER ROLE nl2sql_reader SET idle_in_transaction_session_timeout = '30s';
```

### `.env.example`

Root env - used for docker-compose interpolation.

```ini
OLLAMA_MODEL=qwen2.5-coder:7b
```

### `start.sh`

```bash
#!/bin/bash

echo "========================================="
echo "       QueryLocal - 1-Click Setup"
echo "========================================="
echo ""

# Check for Docker
if ! command -v docker &> /dev/null; then
    echo "[ERROR] Docker is not installed or not running."
    echo "Please install Docker: https://www.docker.com/"
    exit 1
fi

# Check for Ollama
if ! command -v ollama &> /dev/null; then
    echo "[ERROR] Ollama is not installed."
    echo "Please install Ollama: https://ollama.com/"
    exit 1
fi

echo "Which AI model would you like to run?"
echo "(Recommended: qwen2.5-coder:7b)"
read -p "Enter model name (or press Enter for default): " MODEL_NAME

if [ -z "$MODEL_NAME" ]; then
    MODEL_NAME="qwen2.5-coder:7b"
fi

echo ""
echo "Save choice to .env file..."
echo "OLLAMA_MODEL=$MODEL_NAME" > .env

echo ""
echo "Pulling $MODEL_NAME... (This may take a moment if not already downloaded)"
ollama pull "$MODEL_NAME"

echo ""
echo "Starting Docker containers..."
docker-compose up --build
```

### `start.bat`

```batch
@echo off
setlocal

echo =========================================
echo       QueryLocal - 1-Click Setup
echo =========================================
echo.

:: Check for Docker
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not installed or not running.
    echo Please install Docker Desktop: https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

:: Check for Ollama
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Ollama is not installed.
    echo Please install Ollama: https://ollama.com/
    pause
    exit /b 1
)

echo Which AI model would you like to run?
echo (Recommended: qwen2.5-coder:7b)
set /p MODEL_NAME="Enter model name (or press Enter for default): "

if "%MODEL_NAME%"=="" (
    set MODEL_NAME=qwen2.5-coder:7b
)

echo.
echo Save choice to .env file...
echo OLLAMA_MODEL=%MODEL_NAME% > .env

echo.
echo Pulling %MODEL_NAME%... (This may take a moment if not already downloaded)
ollama pull %MODEL_NAME%

echo.
echo Starting Docker containers...
docker-compose up --build

echo.
echo Application stopped.
pause
```

### `kill_ports.bat`

```batch
@echo off
FOR /F "tokens=5" %%a in ('netstat -a -n -o ^| findstr :8000') do taskkill /F /PID %%a
FOR /F "tokens=5" %%a in ('netstat -a -n -o ^| findstr :3000') do taskkill /F /PID %%a
exit /b 0
```


## 18.2 Backend (FastAPI + Python)

### `backend/.env.example`

```ini
# Database Configuration
POSTGRES_USER=nl2sql_reader
POSTGRES_PASSWORD=yourpassword
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5433
POSTGRES_DB=yourdatabase

# LLM Configuration
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen2.5-coder:7b
```

### `backend/requirements.txt`

```text
fastapi
uvicorn
psycopg2-binary
sqlglot
sentence-transformers
chromadb
python-dotenv
requests
httpx
```

### `backend/Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app

# Install build dependencies for psycopg2/chromadb if needed
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `backend/main.py`

**The core of the project.** FastAPI app, `validate_sql` AST gate, and `process_query` - the async generator implementing retrieve -> generate -> validate -> execute -> self-correct -> stream.

```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
import sqlglot
import requests
import time
import json
import asyncio

from database import (
    execute_query, get_db_connection, get_schema_definitions,
    insert_audit_log, get_audit_history
)
from retrieval import index_schema, retrieve_context
from llm import generate_sql, stream_explanation, OLLAMA_BASE_URL

app = FastAPI(title="QueryLocal API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    question: str
    history: list[dict] = []

@app.get("/health")
def health_check():
    db_conn = get_db_connection()
    db_status = "ok" if db_conn else "error"
    if db_conn: db_conn.close()
        
    ollama_status = "error"
    try:
        r = requests.get(OLLAMA_BASE_URL, timeout=2)
        if r.status_code == 200: ollama_status = "ok"
    except: pass
        
    return {"database": db_status, "ollama": ollama_status}

@app.post("/reindex")
def trigger_reindex():
    return index_schema()

@app.get("/schema")
def schema():
    return get_schema_definitions()

@app.get("/history")
def history():
    return get_audit_history()

def validate_sql(sql: str) -> bool:
    try:
        parsed = sqlglot.parse(sql, read="postgres")
        if not parsed: return False
        for node in parsed:
            if not isinstance(node, sqlglot.exp.Select):
                return False
        return True
    except Exception:
        return False

@app.post("/query")
async def process_query(req: QueryRequest):
    async def event_stream():
        start_time = time.time()
        question = req.question
        
        yield f"data: {json.dumps({'type': 'status', 'message': 'Retrieving schema context...'})}\n\n"
        context = retrieve_context(question, top_k=5)
        
        max_attempts = 3
        attempt = 0
        error_msg = None
        sql = ""
        success = False
        result = None
        
        while attempt < max_attempts:
            attempt += 1
            yield f"data: {json.dumps({'type': 'status', 'message': f'Generating SQL (Attempt {attempt})...'})}\n\n"
            
            sql = generate_sql(question, context, history=req.history, error_context=error_msg)
            if not sql:
                error_msg = "LLM failed to return a query."
                continue
                
            yield f"data: {json.dumps({'type': 'status', 'message': f'Validating SQL (Attempt {attempt})...'})}\n\n"
            if not validate_sql(sql):
                error_msg = "Validation Error: Only SELECT queries are allowed, or the SQL is malformed."
                continue
                
            yield f"data: {json.dumps({'type': 'status', 'message': f'Executing SQL (Attempt {attempt})...'})}\n\n"
            result = execute_query(sql)
            if "error" in result:
                error_msg = result["error"]
                continue
                
            success = True
            break
            
        latency_ms = int((time.time() - start_time) * 1000)
        status_str = "Success" if success else "Failed"
        insert_audit_log(question, sql, attempt, latency_ms, status_str)
        
        if not success:
            payload = jsonable_encoder({'type': 'error', 'sql': sql, 'error': f'Failed after {max_attempts} attempts. Last error: {error_msg}', 'attempts': attempt})
            yield f"data: {json.dumps(payload)}\n\n"
            return
            
        # Success: stream initial payload
        payload = jsonable_encoder({'type': 'result', 'sql': sql, 'results': result, 'attempts': attempt, 'latency_ms': latency_ms})
        yield f"data: {json.dumps(payload)}\n\n"
        
        # Now stream the explanation token by token
        yield f"data: {json.dumps({'type': 'status', 'message': 'Generating explanation...'})}\n\n"
        
        from llm import generate_suggestions
        suggestions_task = asyncio.create_task(generate_suggestions(question, sql))
        
        try:
            async for token in stream_explanation(question, sql):
                yield f"data: {json.dumps({'type': 'explanation_token', 'token': token})}\n\n"
        except Exception as e:
            print(f"Explanation streaming error: {e}")
            
        try:
            suggestions = await asyncio.wait_for(suggestions_task, timeout=8.0)
            if suggestions:
                yield f"data: {json.dumps({'type': 'suggestions', 'data': suggestions})}\n\n"
        except Exception as e:
            print(f"Suggestions wait error: {e}")
            
        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### `backend/llm.py`

All three Ollama calls: blocking SQL generation, streamed explanation, and JSON-mode follow-up suggestions. Prompts are f-strings here, not template files.

````python
import os
import requests
import json
from typing import Dict, Any

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")

def generate_sql(question: str, schema_context: list[str], history: list = None, error_context: str = None) -> str:
    """Calls Ollama to generate a SQL query."""
    
    schema_str = "\n".join(schema_context)
    
    prompt = f"""You are a PostgreSQL expert. Your task is to generate a fully correct PostgreSQL query to answer the user's question.
    
CRITICAL RULES:
1. You MUST ONLY use the tables and columns explicitly listed in the Schema context below.
2. DO NOT invent or assume any table or column names that are not in the schema.
3. If a concept (like "enterprise") maps to a column (like "segment"), use a WHERE clause on that column.
4. ALWAYS use ILIKE for string comparisons to ensure case-insensitivity (e.g., segment ILIKE '%enterprise%').
    
Schema context:
{schema_str}

"""
    if history and len(history) > 0:
        prompt += "\n--- PREVIOUS CHAT HISTORY ---\n"
        for h in history[-3:]:
            prompt += f"Question: {h.get('question')}\nSQL: {h.get('sql')}\n\n"
        prompt += "--- END HISTORY ---\n"
    if error_context:
        prompt += f"\nThe previous query failed with this error. Please correct it:\n{error_context}\n"
        
    prompt += f"\nQuestion: {question}\n\nRespond ONLY with the raw SQL query, no markdown formatting, no explanation."
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        sql = data.get("response", "").strip()
        
        # Remove potential markdown block if the model ignores the instruction
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
            
        return sql.strip()
    except Exception as e:
        print(f"LLM Error: {e}")
        return ""

import httpx

async def stream_explanation(question: str, sql: str):
    prompt = f"You are a helpful data analyst. Explain this SQL query in plain English in 1-2 concise sentences. Be very brief.\nQuestion: {question}\nSQL: {sql}\nExplanation:"
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True
    }
    
    async with httpx.AsyncClient() as client:
        async with client.stream("POST", f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=30.0) as response:
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        token = data.get("response", "")
                        if token:
                            yield token
                    except:
                        pass

async def generate_suggestions(question: str, sql: str) -> list:
    prompt = f"Given the user's question: '{question}' and the generated SQL: '{sql}', provide exactly 3 short follow-up questions the user could ask next to dig deeper into this data. Return ONLY a JSON list of strings, for example: [\"Question 1?\", \"Question 2?\", \"Question 3?\"]. Do not include any markdown formatting or explanation."
    
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload, timeout=15.0)
            data = response.json()
            result_text = data.get("response", "[]")
            suggestions = json.loads(result_text)
            if isinstance(suggestions, dict):
                # sometimes models return {"suggestions": [...]}
                for k, v in suggestions.items():
                    if isinstance(v, list):
                        return v[:3]
                return []
            elif isinstance(suggestions, list):
                return suggestions[:3]
            return []
    except Exception as e:
        print(f"Suggestions Error: {e}")
        return []
````

### `backend/retrieval.py`

ChromaDB indexing and retrieval. Note `index_schema` deletes and recreates the whole collection rather than upserting deltas.

```python
import os
import chromadb
from chromadb.utils import embedding_functions
from database import get_schema_definitions

# Initialize ChromaDB persistent client
CHROMA_DATA_PATH = os.path.join(os.path.dirname(__file__), "schema_index")
chroma_client = chromadb.PersistentClient(path=CHROMA_DATA_PATH, settings=chromadb.Settings(anonymized_telemetry=False))

# Use sentence-transformers embedding function
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

COLLECTION_NAME = "database_schema"

def get_collection():
    return chroma_client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=sentence_transformer_ef
    )

def index_schema():
    """Fetches schema from Postgres and indexes it into ChromaDB."""
    schema_docs = get_schema_definitions()
    if not schema_docs:
        print("No schema found to index.")
        return {"status": "error", "message": "No schema retrieved from DB."}
        
    collection = get_collection()
    
    # We can delete existing to re-index, or upsert. Let's delete and recreate for simplicity
    try:
        chroma_client.delete_collection(name=COLLECTION_NAME)
        collection = get_collection()
    except Exception:
        pass
    
    ids = []
    documents = []
    metadatas = []
    
    for doc in schema_docs:
        ids.append(doc["table"])
        documents.append(doc["description"])
        metadatas.append({"table": doc["table"]})
        
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    return {"status": "success", "tables_indexed": len(schema_docs)}

def retrieve_context(query: str, top_k: int = 5):
    """Retrieves top_k relevant tables for a given user query."""
    collection = get_collection()
    results = collection.query(
        query_texts=[query],
        n_results=top_k
    )
    if not results or not results['documents']:
        return []
    
    return results['documents'][0]
```

### `backend/database.py`

Two connection identities: `get_db_connection()` (the read-only `nl2sql_reader` role, used for LLM-generated SQL) and `get_admin_connection()` (writes the audit table). `init_audit_table()` runs at import time.

```python
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DB_USER = os.getenv("POSTGRES_USER", "nl2sql_reader")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "yourpassword")
DB_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
DB_PORT = os.getenv("POSTGRES_PORT", "5433")
DB_NAME = os.getenv("POSTGRES_DB", "yourdatabase")

def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT,
            connect_timeout=5
        )
        # Apply timeout settings per the project requirements
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = 15000;") # 15 seconds
            cur.execute("SET idle_in_transaction_session_timeout = 30000;")
        conn.commit()
        return conn
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def execute_query(query: str, limit: int = 1000):
    """Executes a validated SELECT query and returns the results."""
    conn = get_db_connection()
    if not conn:
        return {"error": "Database connection failed"}
    
    try:
        # We assume query validation is done BEFORE calling this function
        # Enforce a soft limit by injecting it if not present, though we can just wrap it
        # Actually it's safer to run it as a subquery if we want to force limit, 
        # or rely on sqlglot to inject limit. For now we just execute.
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            results = cur.fetchmany(limit)
            return {"columns": [desc[0] for desc in cur.description], "rows": results}
    except Exception as e:
        return {"error": str(e)}
    finally:
        if conn:
            conn.close()

def get_schema_definitions():
    """Extracts schema definitions for indexing."""
    conn = get_db_connection()
    if not conn:
        return []
    
    schema_query = """
    SELECT table_name, column_name, data_type 
    FROM information_schema.columns 
    WHERE table_schema = 'public';
    """
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(schema_query)
            rows = cur.fetchall()
            
            tables = {}
            for row in rows:
                t_name = row['table_name']
                if t_name not in tables:
                    tables[t_name] = []
                tables[t_name].append(f"{row['column_name']} ({row['data_type']})")
                
            schema_docs = []
            for t_name, columns in tables.items():
                schema_docs.append({
                    "table": t_name,
                    "description": f"Table: {t_name}. Columns: {', '.join(columns)}"
                })
            return schema_docs
    except Exception as e:
        print(f"Schema extraction error: {e}")
        return []
    finally:
        if conn:
            conn.close()

ADMIN_USER = os.getenv("POSTGRES_ADMIN_USER", "root")
ADMIN_PASS = os.getenv("POSTGRES_ADMIN_PASSWORD", "rootpassword")

def get_admin_connection():
    try:
        return psycopg2.connect(
            dbname=DB_NAME,
            user=ADMIN_USER,
            password=ADMIN_PASS,
            host=DB_HOST,
            port=DB_PORT,
            connect_timeout=5
        )
    except Exception as e:
        print(f"Admin connection error: {e}")
        return None

def init_audit_table():
    conn = get_admin_connection()
    if not conn: return
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS query_audit (
                    id SERIAL PRIMARY KEY,
                    question TEXT,
                    generated_sql TEXT,
                    attempts INT,
                    latency_ms INT,
                    status VARCHAR(50),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
        conn.commit()
    except Exception as e:
        print(f"Audit table init error: {e}")
    finally:
        conn.close()

def insert_audit_log(question, generated_sql, attempts, latency_ms, status):
    conn = get_admin_connection()
    if not conn: return
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO query_audit (question, generated_sql, attempts, latency_ms, status)
                VALUES (%s, %s, %s, %s, %s)
            """, (question, generated_sql, attempts, latency_ms, status))
        conn.commit()
    except Exception as e:
        print(f"Audit insert error: {e}")
    finally:
        conn.close()

def get_audit_history(limit=50):
    conn = get_admin_connection()
    if not conn: return []
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM query_audit ORDER BY timestamp DESC LIMIT %s", (limit,))
            # Convert datetime to string for JSON serialization
            rows = cur.fetchall()
            for r in rows:
                if r.get('timestamp'):
                    r['timestamp'] = r['timestamp'].isoformat()
            return rows
    except Exception as e:
        print(f"Audit fetch error: {e}")
        return []
    finally:
        conn.close()

init_audit_table()
```

### `backend/seed_db.py`

Idempotent seeder - `TRUNCATE ... RESTART IDENTITY CASCADE` then regenerate.

```python
import psycopg2
import random
from datetime import datetime, timedelta
import string

DB_USER = "root"
DB_PASS = "rootpassword"
DB_HOST = "127.0.0.1"
DB_PORT = "5433"
DB_NAME = "yourdatabase"

schema_sql = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    segment VARCHAR(50),
    signup_date DATE
);

CREATE TABLE IF NOT EXISTS products (
    product_id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    category VARCHAR(50),
    price DECIMAL(10, 2)
);

CREATE TABLE IF NOT EXISTS orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(customer_id),
    order_date DATE,
    total_amount DECIMAL(10, 2),
    status VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INT REFERENCES orders(order_id),
    product_id INT REFERENCES products(product_id),
    quantity INT,
    unit_price DECIMAL(10, 2)
);

-- Truncate existing data
TRUNCATE TABLE order_items, orders, products, customers RESTART IDENTITY CASCADE;
"""

def generate_random_string(length=8):
    return ''.join(random.choices(string.ascii_letters, k=length))

def generate_random_date(start_date, end_date):
    time_between_dates = end_date - start_date
    days_between_dates = time_between_dates.days
    random_number_of_days = random.randrange(days_between_dates)
    return start_date + timedelta(days=random_number_of_days)

def seed_db():
    try:
        print("Connecting to database...")
        conn = psycopg2.connect(dbname=DB_NAME, user=DB_USER, password=DB_PASS, host=DB_HOST, port=DB_PORT)
        with conn.cursor() as cur:
            print("Executing schema script...")
            cur.execute(schema_sql)
            
            # Generate Products
            print("Generating Products...")
            categories = ['Software', 'Hardware', 'Services', 'Consulting']
            products = []
            for i in range(50):
                p_name = f"Product {generate_random_string(5)}"
                cat = random.choice(categories)
                price = round(random.uniform(10.0, 500.0), 2)
                products.append((p_name, cat, price))
            
            psql_insert = "INSERT INTO products (name, category, price) VALUES (%s, %s, %s) RETURNING product_id, price"
            cur.executemany("INSERT INTO products (name, category, price) VALUES (%s, %s, %s)", products)
            cur.execute("SELECT product_id, price FROM products")
            product_data = cur.fetchall()
            
            # Generate Customers
            print("Generating Customers...")
            segments = ['Enterprise', 'SMB', 'Startup', 'Mid-Market']
            start_date = datetime(2021, 1, 1)
            end_date = datetime(2024, 1, 1)
            
            customers = []
            for i in range(1000):
                c_name = f"Company {generate_random_string(6)}"
                email = f"contact@{c_name.lower().replace(' ', '')}.com"
                seg = random.choice(segments)
                s_date = generate_random_date(start_date, end_date)
                customers.append((c_name, email, seg, s_date.date()))
                
            cur.executemany("INSERT INTO customers (name, email, segment, signup_date) VALUES (%s, %s, %s, %s)", customers)
            
            # Generate Orders and Order Items
            print("Generating Orders and Items...")
            orders = []
            order_items = []
            
            statuses = ['Completed', 'Pending', 'Cancelled', 'Refunded']
            
            for o_id in range(1, 5001):
                c_id = random.randint(1, 1000)
                o_date = generate_random_date(start_date, end_date)
                status = random.choices(statuses, weights=[70, 20, 5, 5])[0]
                
                # generate 1 to 5 items for this order
                num_items = random.randint(1, 5)
                order_total = 0
                items_for_this_order = []
                for _ in range(num_items):
                    p_id, price = random.choice(product_data)
                    qty = random.randint(1, 10)
                    items_for_this_order.append((o_id, p_id, qty, price))
                    order_total += float(price) * qty
                    
                orders.append((c_id, o_date.date(), order_total, status))
                order_items.extend(items_for_this_order)
                
            cur.executemany("INSERT INTO orders (customer_id, order_date, total_amount, status) VALUES (%s, %s, %s, %s)", orders)
            cur.executemany("INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (%s, %s, %s, %s)", order_items)
            
        conn.commit()
        print(f"Database seeded successfully with {len(customers)} customers, {len(products)} products, {len(orders)} orders, and {len(order_items)} items!")
    except Exception as e:
        print(f"Error seeding database: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

if __name__ == "__main__":
    seed_db()
```

### `backend/seed_db.sql`

Pure-SQL alternative to the Python seeder.

```sql
CREATE TABLE IF NOT EXISTS customers (
    customer_id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100),
    segment VARCHAR(50),
    signup_date DATE
);

CREATE TABLE IF NOT EXISTS products (
    product_id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    category VARCHAR(50),
    price DECIMAL(10, 2)
);

CREATE TABLE IF NOT EXISTS orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(customer_id),
    order_date DATE,
    total_amount DECIMAL(10, 2),
    status VARCHAR(20)
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id SERIAL PRIMARY KEY,
    order_id INT REFERENCES orders(order_id),
    product_id INT REFERENCES products(product_id),
    quantity INT,
    unit_price DECIMAL(10, 2)
);

TRUNCATE TABLE order_items, orders, products, customers RESTART IDENTITY CASCADE;

INSERT INTO customers (name, email, segment, signup_date) VALUES
('Alice Smith', 'alice@example.com', 'Enterprise', '2023-01-15'),
('Bob Johnson', 'bob@example.com', 'SMB', '2023-03-22'),
('Charlie Brown', 'charlie@example.com', 'Startup', '2023-06-10');

INSERT INTO products (name, category, price) VALUES
('Pro Subscription', 'Software', 99.99),
('Basic Subscription', 'Software', 29.99),
('Consulting Hour', 'Service', 150.00);

INSERT INTO orders (customer_id, order_date, total_amount, status) VALUES
(1, '2023-02-01', 99.99, 'Completed'),
(1, '2023-03-01', 99.99, 'Completed'),
(2, '2023-04-15', 29.99, 'Completed'),
(3, '2023-06-15', 150.00, 'Pending');

INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES
(1, 1, 1, 99.99),
(2, 1, 1, 99.99),
(3, 2, 1, 29.99),
(4, 3, 1, 150.00);
```

### `backend/kill_ports.py`

```python
import os
import psutil
import time
import requests

def kill_port(port):
    for proc in psutil.process_iter(['pid', 'name', 'connections']):
        try:
            for conn in proc.connections(kind='inet'):
                if conn.laddr.port == port:
                    print(f"Killing process {proc.info['pid']} on port {port}")
                    proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

print("Killing 8000 and 3000...")
kill_port(8000)
kill_port(3000)
print("Done killing ports.")
```

### `backend/check_users.sql`

One-off psql admin snippet.

```sql
\du
```

### `backend/reset_passwords.sql`

One-off psql admin snippet. These are the repo's placeholder credentials - change them before any real deployment.

```sql
ALTER ROLE root WITH PASSWORD 'rootpassword';
ALTER ROLE nl2sql_reader WITH PASSWORD 'yourpassword';
```


### Manual smoke scripts

These are *not* an automated test suite - they are throwaway scripts used during development. Their existence is a known gap, not a testing strategy.

### `backend/test_api.py`

```python
import requests

try:
    r = requests.get("http://127.0.0.1:8000/schema", timeout=3)
    print("Schema Response:", r.status_code)
    print(r.json()[:2])
except Exception as e:
    print(f"Backend failed: {e}")
```

### `backend/test_conn.py`

```python
import psycopg2
try:
    conn = psycopg2.connect(dbname="yourdatabase", user="root", password="rootpassword", host="127.0.0.1")
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("ALTER ROLE nl2sql_reader WITH PASSWORD 'yourpassword';")
    print("Success root")
except Exception as e:
    print(f"Failed root: {e}")

try:
    conn = psycopg2.connect(dbname="yourdatabase", user="postgres", password="rootpassword", host="127.0.0.1")
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("ALTER ROLE nl2sql_reader WITH PASSWORD 'yourpassword';")
    print("Success postgres")
except Exception as e:
    print(f"Failed postgres: {e}")
```

### `backend/test_encoder.py`

```python
from fastapi.encoders import jsonable_encoder
from datetime import date
from psycopg2.extras import RealDictRow
import json

# Create a dummy cursor description to initialize RealDictRow properly if needed
# Actually RealDictRow might need a RealDictCursor to initialize, 
# but let's just make a dict subclass.
class DummyRow(dict):
    pass

r = DummyRow()
r['signup_date'] = date(2023, 1, 15)

payload = {'type': 'result', 'results': {'rows': [r]}}
try:
    encoded = jsonable_encoder(payload)
    print("ENCODED:", encoded)
    print("JSON:", json.dumps(encoded))
except Exception as e:
    print("ERROR:", e)
```

### `backend/test_history.py`

```python
import requests
try:
    r = requests.get("http://127.0.0.1:8000/history")
    print(r.status_code)
    print(r.text)
except Exception as e:
    print(e)
```

### `backend/test_openapi.py`

```python
import requests
try:
    r = requests.get("http://127.0.0.1:8000/openapi.json")
    print(r.text)
except Exception as e:
    print(e)
```


## 18.3 Frontend (Next.js 14 + TypeScript)

### `frontend/package.json`

```json
{
  "name": "frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint"
  },
  "dependencies": {
    "@base-ui/react": "^1.6.0",
    "class-variance-authority": "^0.7.1",
    "clsx": "^2.1.1",
    "lucide-react": "^1.26.0",
    "next": "14.2.35",
    "next-themes": "^0.4.6",
    "react": "^18",
    "react-dom": "^18",
    "recharts": "^3.10.1",
    "shadcn": "^4.14.1",
    "tailwind-merge": "^3.6.0",
    "tailwindcss-animate": "^1.0.7",
    "tw-animate-css": "^1.4.0"
  },
  "devDependencies": {
    "@types/node": "^20",
    "@types/react": "^18",
    "@types/react-dom": "^18",
    "eslint": "^8",
    "eslint-config-next": "14.2.35",
    "postcss": "^8",
    "tailwindcss": "^3.4.1",
    "typescript": "^5"
  }
}
```

### `frontend/next.config.mjs`

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {};

export default nextConfig;
```

### `frontend/tsconfig.json`

```json
{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

### `frontend/tailwind.config.ts`

```ts
import type { Config } from "tailwindcss";

const config = {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  prefix: "",
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        card: "var(--card)",
        "card-foreground": "var(--card-foreground)",
        popover: "var(--popover)",
        "popover-foreground": "var(--popover-foreground)",
        primary: "var(--primary)",
        "primary-foreground": "var(--primary-foreground)",
        secondary: "var(--secondary)",
        "secondary-foreground": "var(--secondary-foreground)",
        muted: "var(--muted)",
        "muted-foreground": "var(--muted-foreground)",
        accent: "var(--accent)",
        "accent-foreground": "var(--accent-foreground)",
        destructive: "var(--destructive)",
        border: "var(--border)",
        input: "var(--input)",
        ring: "var(--ring)",
        "sidebar-bg": "var(--sidebar-bg)",
        "sidebar-border": "var(--sidebar-border)",
        "accent-brand": "var(--accent-brand)",
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'monospace'],
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
} satisfies Config;

export default config;
```

### `frontend/components.json`

```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "base-nova",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "src/app/globals.css",
    "baseColor": "neutral",
    "cssVariables": true,
    "prefix": ""
  },
  "iconLibrary": "lucide",
  "rtl": false,
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils",
    "ui": "@/components/ui",
    "lib": "@/lib",
    "hooks": "@/hooks"
  },
  "menuColor": "default",
  "menuAccent": "subtle",
  "registries": {}
}
```

### `frontend/Dockerfile`

```dockerfile
FROM node:18-alpine
WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]
```

### `frontend/src/app/layout.tsx`

```tsx
import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { ThemeProvider } from "@/components/theme-provider";

const inter = Inter({ subsets: ["latin"], variable: "--font-sans" });
const jetbrainsMono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "AskBase — Natural Language SQL",
  description: "Ask questions about your database in plain English. Fully local, privacy-first.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${jetbrainsMono.variable} font-sans antialiased`}>
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
          {children}
        </ThemeProvider>
      </body>
    </html>
  );
}
```

### `frontend/src/app/globals.css`

The whole design system: CSS variables for light and dark, flipped by a single `.dark` class.

```css
@import "tw-animate-css";
@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: #ffffff;
    --foreground: #0d0d0d;
    --card: #f9f9f9;
    --card-foreground: #0d0d0d;
    --popover: #ffffff;
    --popover-foreground: #0d0d0d;
    --primary: #0d0d0d;
    --primary-foreground: #ffffff;
    --secondary: #f5f5f5;
    --secondary-foreground: #0d0d0d;
    --muted: #f5f5f5;
    --muted-foreground: #737373;
    --accent: #f5f5f5;
    --accent-foreground: #0d0d0d;
    --destructive: #dc2626;
    --border: #e5e5e5;
    --input: #e5e5e5;
    --ring: #0d0d0d;
    --radius: 0.75rem;
    --sidebar-bg: #f9f9f9;
    --sidebar-border: #ebebeb;
    --accent-brand: #2563eb;
  }

  .dark {
    --background: #212121;
    --foreground: #ececec;
    --card: #2f2f2f;
    --card-foreground: #ececec;
    --popover: #2f2f2f;
    --popover-foreground: #ececec;
    --primary: #ececec;
    --primary-foreground: #212121;
    --secondary: #2f2f2f;
    --secondary-foreground: #ececec;
    --muted: #2f2f2f;
    --muted-foreground: #a0a0a0;
    --accent: #2f2f2f;
    --accent-foreground: #ececec;
    --destructive: #f87171;
    --border: #3e3e3e;
    --input: #3e3e3e;
    --ring: #ececec;
    --sidebar-bg: #171717;
    --sidebar-border: #2f2f2f;
    --accent-brand: #7c9cff;
  }

  * {
    border-color: var(--border);
  }
  body {
    background-color: var(--background);
    color: var(--foreground);
  }
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--border); border-radius: 999px; }
::-webkit-scrollbar-thumb:hover { background: var(--muted-foreground); }

/* ── Animations ── */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.animate-fade-in {
  animation: fadeIn 0.3s ease-out forwards;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
.animate-pulse {
  animation: pulse 2s ease-in-out infinite;
}

/* ── Code blocks ── */
.sql-block {
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 8px;
  overflow: hidden;
}
.sql-block pre {
  padding: 16px;
  font-size: 13px;
  line-height: 1.6;
  overflow-x: auto;
}

/* ── Typing cursor ── */
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}
.typing-cursor::after {
  content: '▋';
  animation: blink 1s step-end infinite;
  color: var(--accent-brand);
}
```

### `frontend/src/app/page.tsx`

**The entire client application in one `"use client"` component** - chat state, the hand-rolled SSE parser, the results table, the auto-charting heuristic, voice input, the schema sidebar and the history modal.

```tsx
/* eslint-disable @typescript-eslint/no-unused-vars, @typescript-eslint/no-explicit-any, react/no-unescaped-entities */
"use client";

import { useState, useEffect, useRef } from "react";
import { useTheme } from "next-themes";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip as RechartsTooltip, ResponsiveContainer, Cell,
} from "recharts";

/* ── Icons (inline SVGs to avoid bloat) ── */
const IconSend = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 2 11 13"/><path d="M22 2 15 22 11 13 2 9z"/></svg>
);
const IconMic = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" x2="12" y1="19" y2="22"/></svg>
);
const IconPlus = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>
);
const IconHistory = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/></svg>
);
const IconDatabase = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5"/><path d="M3 12c0 1.66 4.03 3 9 3s9-1.34 9-3"/></svg>
);
const IconTable = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3v18"/><rect width="18" height="18" x="3" y="3" rx="2"/><path d="M3 9h18"/><path d="M3 15h18"/></svg>
);
const IconChart = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" x2="18" y1="20" y2="10"/><line x1="12" x2="12" y1="20" y2="4"/><line x1="6" x2="6" y1="20" y2="14"/></svg>
);
const IconX = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
);
const IconChevron = ({ open }: { open: boolean }) => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={`transition-transform duration-200 ${open ? 'rotate-90' : ''}`}><path d="m9 18 6-6-6-6"/></svg>
);
const IconCode = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
);
const IconCopy = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="14" height="14" x="8" y="8" rx="2" ry="2"/><path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"/></svg>
);
const IconCheck = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M20 6 9 17l-5-5"/></svg>
);
const IconSun = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>
);
const IconMoon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>
);

const CHART_COLORS = ["#7c9cff", "#f59e0b", "#10b981", "#f472b6", "#8b5cf6", "#06b6d4"];

export default function Home() {
  const { theme, setTheme } = useTheme();
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [schema, setSchema] = useState<any[]>([]);
  const [mounted, setMounted] = useState(false);
  const [copiedSql, setCopiedSql] = useState(false);

  // Conversation state
  const [messages, setMessages] = useState<any[]>([]);
  const [chatHistory, setChatHistory] = useState<{question: string, sql: string}[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([
    "How many total products are there?",
    "What is the average order amount?",
    "Show me the top 5 customers by revenue",
  ]);

  // Sidebar
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [schemaExpanded, setSchemaExpanded] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [history, setHistory] = useState<any[]>([]);
  const [expandedTable, setExpandedTable] = useState<number | null>(null);

  // Results view
  const [activeTab, setActiveTab] = useState<"table" | "chart">("table");

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    fetch("http://localhost:8000/schema")
      .then((res) => res.json())
      .then((data) => setSchema(data))
      .catch(() => {});
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadHistory = () => {
    fetch("http://localhost:8000/history")
      .then((res) => res.ok ? res.json() : [])
      .then((data) => { setHistory(Array.isArray(data) ? data : []); setHistoryOpen(true); })
      .catch(() => { setHistory([]); setHistoryOpen(true); });
  };

  const toggleListening = () => {
    if (isListening) { setIsListening(false); return; }
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) { alert("Speech Recognition not supported."); return; }
    const recognition = new SR();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = "en-US";
    recognition.onstart = () => setIsListening(true);
    recognition.onresult = (event: any) => {
      const transcript = Array.from(event.results).map((r: any) => r[0].transcript).join("");
      setQuestion(transcript);
    };
    recognition.onerror = () => setIsListening(false);
    recognition.onend = () => setIsListening(false);
    recognition.start();
  };

  const copySql = (sql: string) => {
    navigator.clipboard.writeText(sql);
    setCopiedSql(true);
    setTimeout(() => setCopiedSql(false), 2000);
  };

  const handleQuery = async (e?: React.FormEvent, directQ?: string) => {
    if (e) e.preventDefault();
    const q = directQ || question;
    if (!q.trim() || loading) return;

    // Add user message
    const userMsg = { role: "user", content: q };
    const assistantMsg = { role: "assistant", content: "", sql: "", results: null, error: "", attempts: 0, latency: 0, loading: true, explanation: "" };
    setMessages(prev => [...prev, userMsg, assistantMsg]);
    setQuestion("");
    setLoading(true);

    try {
      const res = await fetch("http://localhost:8000/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, history: chatHistory }),
      });
      if (!res.body) throw new Error("No response body");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let boundary = buffer.indexOf("\n\n");
        while (boundary !== -1) {
          const line = buffer.slice(0, boundary);
          buffer = buffer.slice(boundary + 2);
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.substring(6));
              setMessages(prev => {
                const updated = [...prev];
                const last = { ...updated[updated.length - 1] };
                if (data.type === "status") last.content = data.message;
                else if (data.type === "error") { last.error = data.error; last.sql = data.sql || ""; last.attempts = data.attempts; last.loading = false; }
                else if (data.type === "result") { last.sql = data.sql; last.results = data.results; last.attempts = data.attempts; last.latency = data.latency_ms; last.content = ""; setChatHistory(p => [...p, { question: q, sql: data.sql }]); }
                else if (data.type === "explanation_token") last.explanation = (last.explanation || "") + data.token;
                else if (data.type === "suggestions") { if (Array.isArray(data.data) && data.data.length > 0) setSuggestions(data.data); }
                else if (data.type === "done") { last.loading = false; }
                updated[updated.length - 1] = last;
                return updated;
              });
            } catch {}
          }
          boundary = buffer.indexOf("\n\n");
        }
      }
    } catch (err: any) {
      setMessages(prev => {
        const updated = [...prev];
        const last = { ...updated[updated.length - 1] };
        last.error = err.message || "Failed to connect to backend.";
        last.loading = false;
        updated[updated.length - 1] = last;
        return updated;
      });
    } finally {
      setLoading(false);
      setMessages(prev => {
        const updated = [...prev];
        const last = { ...updated[updated.length - 1] };
        last.loading = false;
        updated[updated.length - 1] = last;
        return updated;
      });
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleQuery();
    }
  };

  const newChat = () => {
    setMessages([]);
    setChatHistory([]);
    setQuestion("");
    setSuggestions([
      "How many total products are there?",
      "What is the average order amount?",
      "Show me the top 5 customers by revenue",
    ]);
  };

  const hasMessages = messages.length > 0;

  return (
    <div className="h-screen flex bg-background text-foreground overflow-hidden">
      {/* ─── Sidebar ─── */}
      {sidebarOpen && (
        <aside className="w-[260px] flex-shrink-0 bg-sidebar-bg border-r border-sidebar-border flex flex-col h-full">
          {/* New Chat Button */}
          <div className="p-3">
            <button
              onClick={newChat}
              className="w-full flex items-center gap-2 px-3 py-2.5 rounded-lg border border-border text-sm font-medium hover:bg-muted transition-colors"
            >
              <IconPlus />
              New chat
            </button>
          </div>

          {/* Schema Section */}
          <div className="flex-1 overflow-y-auto px-3">
            <button
              onClick={() => setSchemaExpanded(!schemaExpanded)}
              className="w-full flex items-center gap-2 px-2 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider hover:text-foreground transition-colors"
            >
              <IconChevron open={schemaExpanded} />
              <IconDatabase />
              Schema ({schema.length} tables)
            </button>

            {schemaExpanded && (
              <div className="pl-4 space-y-0.5 mb-4">
                {schema.map((table: any, idx: number) => (
                  <div key={idx}>
                    <button
                      onClick={() => setExpandedTable(expandedTable === idx ? null : idx)}
                      className="w-full text-left px-2 py-1.5 text-[13px] font-mono text-muted-foreground hover:text-foreground hover:bg-muted rounded transition-colors flex items-center gap-2"
                    >
                      <span className="truncate">{table.table}</span>
                    </button>
                    {expandedTable === idx && table.description && (
                      <p className="px-2 py-1 text-[11px] text-muted-foreground leading-relaxed border-l-2 border-border ml-2 mb-1">
                        {table.description}
                      </p>
                    )}
                  </div>
                ))}
                {schema.length === 0 && (
                  <p className="px-2 py-2 text-xs text-muted-foreground">No schema loaded</p>
                )}
              </div>
            )}
          </div>

          {/* Sidebar Footer */}
          <div className="border-t border-sidebar-border p-3 space-y-1">
            <button
              onClick={loadHistory}
              className="w-full flex items-center gap-2 px-2 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors"
            >
              <IconHistory />
              History
            </button>
            <button
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
              className="w-full flex items-center gap-2 px-2 py-2 text-sm text-muted-foreground hover:text-foreground hover:bg-muted rounded-lg transition-colors"
            >
              {mounted && theme === "dark" ? <IconSun /> : <IconMoon />}
              {mounted && theme === "dark" ? "Light mode" : "Dark mode"}
            </button>
            <div className="flex items-center gap-1.5 px-2 py-1.5 text-[11px] text-muted-foreground">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              On-premise · No data leaves your machine
            </div>
          </div>
        </aside>
      )}

      {/* ─── Main Area ─── */}
      <main className="flex-1 flex flex-col h-full min-w-0">

        {/* ─── Empty State ─── */}
        {!hasMessages && (
          <div className="flex-1 flex flex-col items-center justify-center px-6">
            <div className="max-w-2xl w-full text-center">
              <h1 className="text-3xl font-semibold mb-2 tracking-tight">AskBase</h1>
              <p className="text-muted-foreground text-base mb-10">
                Ask questions about your database in plain English.
              </p>

              {/* Suggestions */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-12">
                {suggestions.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => handleQuery(undefined, s)}
                    className="text-left p-4 rounded-xl border border-border hover:bg-muted transition-colors group"
                  >
                    <p className="text-sm text-foreground leading-snug">{s}</p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ─── Chat Messages ─── */}
        {hasMessages && (
          <div className="flex-1 overflow-y-auto">
            <div className="max-w-3xl mx-auto px-6 py-8 space-y-6">
              {messages.map((msg, i) => (
                <div key={i} className="animate-fade-in">
                  {msg.role === "user" ? (
                    /* User Message */
                    <div className="flex justify-end">
                      <div className="bg-muted rounded-2xl rounded-br-md px-4 py-3 max-w-[80%]">
                        <p className="text-sm leading-relaxed">{msg.content}</p>
                      </div>
                    </div>
                  ) : (
                    /* Assistant Message */
                    <div className="space-y-4">
                      {/* Loading / Status */}
                      {msg.loading && msg.content && (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <div className="w-4 h-4 border-2 border-muted-foreground/30 border-t-muted-foreground rounded-full animate-spin" />
                          {msg.content}
                        </div>
                      )}
                      {msg.loading && !msg.content && (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                          <div className="w-4 h-4 border-2 border-muted-foreground/30 border-t-muted-foreground rounded-full animate-spin" />
                          Thinking...
                        </div>
                      )}

                      {/* Error */}
                      {msg.error && (
                        <div className="bg-destructive/10 border border-destructive/20 rounded-lg p-4">
                          <p className="text-sm text-destructive font-mono whitespace-pre-wrap">{msg.error}</p>
                        </div>
                      )}

                      {/* SQL Block */}
                      {msg.sql && (
                        <div className="sql-block">
                          <div className="flex items-center justify-between px-4 py-2.5 border-b border-border bg-muted/50">
                            <div className="flex items-center gap-2 text-xs text-muted-foreground font-medium">
                              <IconCode />
                              SQL
                              {msg.latency > 0 && (
                                <span className="ml-2 text-emerald-600 dark:text-emerald-400">{msg.latency}ms</span>
                              )}
                              {msg.attempts > 1 && (
                                <span className="ml-1 text-amber-600 dark:text-amber-400">{msg.attempts} attempts</span>
                              )}
                            </div>
                            <button
                              onClick={() => copySql(msg.sql)}
                              className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground transition-colors"
                            >
                              {copiedSql ? <><IconCheck /> Copied</> : <><IconCopy /> Copy</>}
                            </button>
                          </div>
                          <pre className="text-sm font-mono text-foreground leading-relaxed whitespace-pre-wrap p-4">
                            {msg.sql}
                          </pre>
                        </div>
                      )}

                      {/* Explanation */}
                      {msg.explanation && !msg.loading && (
                        <p className="text-sm text-foreground leading-relaxed">{msg.explanation}</p>
                      )}
                      {msg.explanation && msg.loading && (
                        <p className="text-sm text-foreground leading-relaxed typing-cursor">{msg.explanation}</p>
                      )}

                      {/* Results */}
                      {msg.results && (
                        <div className="border border-border rounded-lg overflow-hidden">
                          {/* Tab bar */}
                          <div className="flex items-center border-b border-border bg-muted/30">
                            <button
                              onClick={() => setActiveTab("table")}
                              className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium transition-colors border-b-2 ${
                                activeTab === "table"
                                  ? "border-foreground text-foreground"
                                  : "border-transparent text-muted-foreground hover:text-foreground"
                              }`}
                            >
                              <IconTable /> Table
                            </button>
                            <button
                              onClick={() => setActiveTab("chart")}
                              className={`flex items-center gap-1.5 px-4 py-2.5 text-xs font-medium transition-colors border-b-2 ${
                                activeTab === "chart"
                                  ? "border-foreground text-foreground"
                                  : "border-transparent text-muted-foreground hover:text-foreground"
                              }`}
                            >
                              <IconChart /> Chart
                            </button>
                            <span className="ml-auto pr-4 text-[11px] text-muted-foreground font-mono">
                              {msg.results.rows?.length || 0} rows
                            </span>
                          </div>

                          {activeTab === "table" ? (
                            <div className="max-h-[400px] overflow-auto">
                              <table className="w-full text-left">
                                <thead className="bg-muted/50 sticky top-0">
                                  <tr>
                                    {msg.results.columns?.map((col: string) => (
                                      <th key={col} className="px-4 py-2.5 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider whitespace-nowrap border-b border-border">
                                        {col}
                                      </th>
                                    ))}
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-border">
                                  {msg.results.rows?.map((row: any, ri: number) => (
                                    <tr key={ri} className="hover:bg-muted/30 transition-colors">
                                      {msg.results.columns?.map((col: string) => (
                                        <td key={col} className="px-4 py-2.5 text-sm font-mono whitespace-nowrap">
                                          {row[col] === null || row[col] === undefined
                                            ? <span className="text-muted-foreground/40 italic text-xs">null</span>
                                            : typeof row[col] === "number"
                                              ? <span className="text-accent-brand">{row[col].toLocaleString()}</span>
                                              : String(row[col])
                                          }
                                        </td>
                                      ))}
                                    </tr>
                                  ))}
                                  {(!msg.results.rows || msg.results.rows.length === 0) && (
                                    <tr>
                                      <td colSpan={msg.results.columns?.length || 1} className="px-4 py-8 text-center text-sm text-muted-foreground">
                                        Query returned no results.
                                      </td>
                                    </tr>
                                  )}
                                </tbody>
                              </table>
                            </div>
                          ) : (
                            <div className="p-6 h-[320px]">
                              {(() => {
                                let xKey = "", yKey = "";
                                if (msg.results.columns) {
                                  for (const col of msg.results.columns) {
                                    const val = msg.results.rows[0]?.[col];
                                    if (typeof val === "number" && !yKey) yKey = col;
                                    else if (!xKey) xKey = col;
                                  }
                                  if (!xKey && msg.results.columns.length > 0) xKey = msg.results.columns[0];
                                  if (!yKey && msg.results.columns.length > 1) yKey = msg.results.columns[1];
                                }
                                if (xKey && yKey) {
                                  return (
                                    <ResponsiveContainer width="100%" height="100%">
                                      <BarChart data={msg.results.rows} margin={{ top: 10, right: 10, left: -10, bottom: 20 }}>
                                        <CartesianGrid strokeDasharray="3 3" opacity={0.15} vertical={false} />
                                        <XAxis dataKey={xKey} fontSize={11} tickLine={false} axisLine={false} angle={-30} textAnchor="end" height={50} stroke="var(--muted-foreground)" />
                                        <YAxis fontSize={11} tickLine={false} axisLine={false} stroke="var(--muted-foreground)" tickFormatter={(v) => v >= 1000 ? `${(v/1000).toFixed(1)}k` : v} />
                                        <RechartsTooltip
                                          cursor={false}
                                          contentStyle={{
                                            backgroundColor: 'var(--card)',
                                            border: '1px solid var(--border)',
                                            borderRadius: '8px',
                                            fontSize: '12px',
                                            color: 'var(--foreground)',
                                            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                                          }}
                                          labelStyle={{ color: 'var(--foreground)', fontWeight: 600, marginBottom: '4px' }}
                                          itemStyle={{ color: 'var(--muted-foreground)' }}
                                        />
                                        <Bar dataKey={yKey} radius={[4, 4, 0, 0]} maxBarSize={48}>
                                          {msg.results.rows?.map((_: any, idx: number) => (
                                            <Cell key={idx} fill={CHART_COLORS[idx % CHART_COLORS.length]} />
                                          ))}
                                        </Bar>
                                      </BarChart>
                                    </ResponsiveContainer>
                                  );
                                }
                                return (
                                  <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
                                    Not enough numeric data to visualize.
                                  </div>
                                );
                              })()}
                            </div>
                          )}
                        </div>
                      )}

                      {/* Follow-up suggestions */}
                      {msg.results && !msg.loading && suggestions.length > 0 && (
                        <div className="flex flex-wrap gap-2 pt-2">
                          {suggestions.map((s, si) => (
                            <button
                              key={si}
                              onClick={() => handleQuery(undefined, s)}
                              className="text-xs px-3 py-1.5 rounded-full border border-border text-muted-foreground hover:text-foreground hover:bg-muted transition-colors"
                            >
                              {s}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          </div>
        )}

        {/* ─── Input Area ─── */}
        <div className={`border-t border-border bg-background px-6 py-4 ${!hasMessages ? '' : ''}`}>
          <div className="max-w-3xl mx-auto">
            <form onSubmit={handleQuery}>
              <div className="relative flex items-end bg-muted rounded-2xl border border-border focus-within:border-foreground/30 transition-colors">
                <textarea
                  ref={inputRef}
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask about your data..."
                  disabled={loading}
                  rows={1}
                  className="flex-1 bg-transparent resize-none px-4 py-3.5 text-sm outline-none placeholder:text-muted-foreground min-h-[48px] max-h-[200px]"
                  style={{ lineHeight: '1.5' }}
                />
                <div className="flex items-center gap-1 pr-2 pb-2">
                  <button
                    type="button"
                    onClick={toggleListening}
                    className={`p-2 rounded-lg transition-colors ${
                      isListening ? "text-destructive bg-destructive/10" : "text-muted-foreground hover:text-foreground hover:bg-background"
                    }`}
                    title="Voice input"
                  >
                    <IconMic />
                  </button>
                  <button
                    type="submit"
                    disabled={loading || !question.trim()}
                    className="p-2 rounded-lg bg-foreground text-background disabled:opacity-30 disabled:cursor-not-allowed hover:opacity-80 transition-opacity"
                  >
                    <IconSend />
                  </button>
                </div>
              </div>
            </form>
            <p className="text-[11px] text-muted-foreground text-center mt-2">
              AskBase generates SQL from natural language. Always verify results.
            </p>
          </div>
        </div>
      </main>

      {/* ─── History Modal ─── */}
      {historyOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" onClick={() => setHistoryOpen(false)}>
          <div className="bg-card border border-border shadow-xl w-full max-w-2xl max-h-[80vh] rounded-2xl flex flex-col mx-4 animate-fade-in" onClick={(e) => e.stopPropagation()}>
            <div className="px-6 py-4 border-b border-border flex justify-between items-center">
              <h2 className="text-base font-semibold">Query History</h2>
              <button onClick={() => setHistoryOpen(false)} className="p-1 rounded hover:bg-muted transition-colors">
                <IconX />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {history.length === 0 ? (
                <p className="text-center py-12 text-sm text-muted-foreground">No queries in history yet.</p>
              ) : (
                history.map((h, i) => (
                  <button
                    key={i}
                    onClick={() => { setHistoryOpen(false); handleQuery(undefined, h.question); }}
                    className="w-full text-left p-4 rounded-lg border border-border hover:bg-muted transition-colors space-y-2"
                  >
                    <div className="flex justify-between items-start gap-3">
                      <p className="text-sm font-medium">{h.question}</p>
                      <span className={`text-[10px] font-medium uppercase px-2 py-0.5 rounded ${
                        h.status === "Success" ? "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                      }`}>
                        {h.status}
                      </span>
                    </div>
                    <pre className="text-xs font-mono text-muted-foreground truncate">{h.generated_sql || "N/A"}</pre>
                  </button>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

### `frontend/src/components/theme-provider.tsx`

```tsx
"use client";

import * as React from "react";
import { ThemeProvider as NextThemesProvider } from "next-themes";
import { type ThemeProviderProps } from "next-themes";

export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  return <NextThemesProvider {...props}>{children}</NextThemesProvider>;
}
```

### `frontend/src/lib/utils.ts`

```ts
import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
```


### shadcn/ui components

### `frontend/src/components/ui/badge.tsx`

```tsx
import { mergeProps } from "@base-ui/react/merge-props"
import { useRender } from "@base-ui/react/use-render"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const badgeVariants = cva(
  "group/badge inline-flex h-5 w-fit shrink-0 items-center justify-center gap-1 overflow-hidden rounded-4xl border border-transparent px-2 py-0.5 text-xs font-medium whitespace-nowrap transition-all focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 aria-invalid:border-destructive aria-invalid:ring-destructive/20 dark:aria-invalid:ring-destructive/40 [&>svg]:pointer-events-none [&>svg]:size-3!",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground [a]:hover:bg-primary/80",
        secondary:
          "bg-secondary text-secondary-foreground [a]:hover:bg-secondary/80",
        destructive:
          "bg-destructive/10 text-destructive focus-visible:ring-destructive/20 dark:bg-destructive/20 dark:focus-visible:ring-destructive/40 [a]:hover:bg-destructive/20",
        outline:
          "border-border text-foreground [a]:hover:bg-muted [a]:hover:text-muted-foreground",
        ghost:
          "hover:bg-muted hover:text-muted-foreground dark:hover:bg-muted/50",
        link: "text-primary underline-offset-4 hover:underline",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  }
)

function Badge({
  className,
  variant = "default",
  render,
  ...props
}: useRender.ComponentProps<"span"> & VariantProps<typeof badgeVariants>) {
  return useRender({
    defaultTagName: "span",
    props: mergeProps<"span">(
      {
        className: cn(badgeVariants({ variant }), className),
      },
      props
    ),
    render,
    state: {
      slot: "badge",
      variant,
    },
  })
}

export { Badge, badgeVariants }
```

### `frontend/src/components/ui/button.tsx`

```tsx
import { Button as ButtonPrimitive } from "@base-ui/react/button"
import { cva, type VariantProps } from "class-variance-authority"

import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "group/button inline-flex shrink-0 items-center justify-center rounded-lg border border-transparent bg-clip-padding text-sm font-medium whitespace-nowrap transition-all outline-none select-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 active:not-aria-[haspopup]:translate-y-px disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/80",
        outline:
          "border-border bg-background hover:bg-muted hover:text-foreground aria-expanded:bg-muted aria-expanded:text-foreground dark:border-input dark:bg-input/30 dark:hover:bg-input/50",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-[color-mix(in_oklch,var(--secondary),var(--foreground)_5%)] aria-expanded:bg-secondary aria-expanded:text-secondary-foreground",
        ghost:
          "hover:bg-muted hover:text-foreground aria-expanded:bg-muted aria-expanded:text-foreground dark:hover:bg-muted/50",
        destructive:
          "bg-destructive/10 text-destructive hover:bg-destructive/20 focus-visible:border-destructive/40 focus-visible:ring-destructive/20 dark:bg-destructive/20 dark:hover:bg-destructive/30 dark:focus-visible:ring-destructive/40",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default:
          "h-8 gap-1.5 px-2.5 has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2",
        xs: "h-6 gap-1 rounded-[min(var(--radius-md),10px)] px-2 text-xs in-data-[slot=button-group]:rounded-lg has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 [&_svg:not([class*='size-'])]:size-3",
        sm: "h-7 gap-1 rounded-[min(var(--radius-md),12px)] px-2.5 text-[0.8rem] in-data-[slot=button-group]:rounded-lg has-data-[icon=inline-end]:pr-1.5 has-data-[icon=inline-start]:pl-1.5 [&_svg:not([class*='size-'])]:size-3.5",
        lg: "h-9 gap-1.5 px-2.5 has-data-[icon=inline-end]:pr-2 has-data-[icon=inline-start]:pl-2",
        icon: "size-8",
        "icon-xs":
          "size-6 rounded-[min(var(--radius-md),10px)] in-data-[slot=button-group]:rounded-lg [&_svg:not([class*='size-'])]:size-3",
        "icon-sm":
          "size-7 rounded-[min(var(--radius-md),12px)] in-data-[slot=button-group]:rounded-lg",
        "icon-lg": "size-9",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

function Button({
  className,
  variant = "default",
  size = "default",
  ...props
}: ButtonPrimitive.Props & VariantProps<typeof buttonVariants>) {
  return (
    <ButtonPrimitive
      data-slot="button"
      className={cn(buttonVariants({ variant, size, className }))}
      {...props}
    />
  )
}

export { Button, buttonVariants }
```

### `frontend/src/components/ui/card.tsx`

```tsx
import * as React from "react"

import { cn } from "@/lib/utils"

function Card({
  className,
  size = "default",
  ...props
}: React.ComponentProps<"div"> & { size?: "default" | "sm" }) {
  return (
    <div
      data-slot="card"
      data-size={size}
      className={cn(
        "group/card flex flex-col gap-(--card-spacing) overflow-hidden rounded-xl bg-card py-(--card-spacing) text-sm text-card-foreground ring-1 ring-foreground/10 [--card-spacing:--spacing(4)] has-data-[slot=card-footer]:pb-0 has-[>img:first-child]:pt-0 data-[size=sm]:[--card-spacing:--spacing(3)] data-[size=sm]:has-data-[slot=card-footer]:pb-0 *:[img:first-child]:rounded-t-xl *:[img:last-child]:rounded-b-xl",
        className
      )}
      {...props}
    />
  )
}

function CardHeader({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-header"
      className={cn(
        "group/card-header @container/card-header grid auto-rows-min items-start gap-1 rounded-t-xl px-(--card-spacing) has-data-[slot=card-action]:grid-cols-[1fr_auto] has-data-[slot=card-description]:grid-rows-[auto_auto] [.border-b]:pb-(--card-spacing)",
        className
      )}
      {...props}
    />
  )
}

function CardTitle({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-title"
      className={cn(
        "font-heading text-base leading-snug font-medium group-data-[size=sm]/card:text-sm",
        className
      )}
      {...props}
    />
  )
}

function CardDescription({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-description"
      className={cn("text-sm text-muted-foreground", className)}
      {...props}
    />
  )
}

function CardAction({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-action"
      className={cn(
        "col-start-2 row-span-2 row-start-1 self-start justify-self-end",
        className
      )}
      {...props}
    />
  )
}

function CardContent({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-content"
      className={cn("px-(--card-spacing)", className)}
      {...props}
    />
  )
}

function CardFooter({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="card-footer"
      className={cn(
        "flex items-center rounded-b-xl border-t bg-muted/50 p-(--card-spacing)",
        className
      )}
      {...props}
    />
  )
}

export {
  Card,
  CardHeader,
  CardFooter,
  CardTitle,
  CardAction,
  CardDescription,
  CardContent,
}
```

### `frontend/src/components/ui/input.tsx`

```tsx
import * as React from "react"
import { Input as InputPrimitive } from "@base-ui/react/input"

import { cn } from "@/lib/utils"

function Input({ className, type, ...props }: React.ComponentProps<"input">) {
  return (
    <InputPrimitive
      type={type}
      data-slot="input"
      className={cn(
        "h-8 w-full min-w-0 rounded-lg border border-input bg-transparent px-2.5 py-1 text-base transition-colors outline-none file:inline-flex file:h-6 file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 disabled:pointer-events-none disabled:cursor-not-allowed disabled:bg-input/50 disabled:opacity-50 aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20 md:text-sm dark:bg-input/30 dark:disabled:bg-input/80 dark:aria-invalid:border-destructive/50 dark:aria-invalid:ring-destructive/40",
        className
      )}
      {...props}
    />
  )
}

export { Input }
```

### `frontend/src/components/ui/scroll-area.tsx`

```tsx
"use client"

import * as React from "react"
import { ScrollArea as ScrollAreaPrimitive } from "@base-ui/react/scroll-area"

import { cn } from "@/lib/utils"

function ScrollArea({
  className,
  children,
  ...props
}: ScrollAreaPrimitive.Root.Props) {
  return (
    <ScrollAreaPrimitive.Root
      data-slot="scroll-area"
      className={cn("relative", className)}
      {...props}
    >
      <ScrollAreaPrimitive.Viewport
        data-slot="scroll-area-viewport"
        className="size-full rounded-[inherit] transition-[color,box-shadow] outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-1"
      >
        {children}
      </ScrollAreaPrimitive.Viewport>
      <ScrollBar />
      <ScrollAreaPrimitive.Corner />
    </ScrollAreaPrimitive.Root>
  )
}

function ScrollBar({
  className,
  orientation = "vertical",
  ...props
}: ScrollAreaPrimitive.Scrollbar.Props) {
  return (
    <ScrollAreaPrimitive.Scrollbar
      data-slot="scroll-area-scrollbar"
      data-orientation={orientation}
      orientation={orientation}
      className={cn(
        "flex touch-none p-px transition-colors select-none data-horizontal:h-2.5 data-horizontal:flex-col data-horizontal:border-t data-horizontal:border-t-transparent data-vertical:h-full data-vertical:w-2.5 data-vertical:border-l data-vertical:border-l-transparent",
        className
      )}
      {...props}
    >
      <ScrollAreaPrimitive.Thumb
        data-slot="scroll-area-thumb"
        className="relative flex-1 rounded-full bg-border"
      />
    </ScrollAreaPrimitive.Scrollbar>
  )
}

export { ScrollArea, ScrollBar }
```

### `frontend/src/components/ui/table.tsx`

```tsx
"use client"

import * as React from "react"

import { cn } from "@/lib/utils"

function Table({ className, ...props }: React.ComponentProps<"table">) {
  return (
    <div
      data-slot="table-container"
      className="relative w-full overflow-x-auto"
    >
      <table
        data-slot="table"
        className={cn("w-full caption-bottom text-sm", className)}
        {...props}
      />
    </div>
  )
}

function TableHeader({ className, ...props }: React.ComponentProps<"thead">) {
  return (
    <thead
      data-slot="table-header"
      className={cn("[&_tr]:border-b", className)}
      {...props}
    />
  )
}

function TableBody({ className, ...props }: React.ComponentProps<"tbody">) {
  return (
    <tbody
      data-slot="table-body"
      className={cn("[&_tr:last-child]:border-0", className)}
      {...props}
    />
  )
}

function TableFooter({ className, ...props }: React.ComponentProps<"tfoot">) {
  return (
    <tfoot
      data-slot="table-footer"
      className={cn(
        "border-t bg-muted/50 font-medium [&>tr]:last:border-b-0",
        className
      )}
      {...props}
    />
  )
}

function TableRow({ className, ...props }: React.ComponentProps<"tr">) {
  return (
    <tr
      data-slot="table-row"
      className={cn(
        "border-b transition-colors hover:bg-muted/50 has-aria-expanded:bg-muted/50 data-[state=selected]:bg-muted",
        className
      )}
      {...props}
    />
  )
}

function TableHead({ className, ...props }: React.ComponentProps<"th">) {
  return (
    <th
      data-slot="table-head"
      className={cn(
        "h-10 px-2 text-left align-middle font-medium whitespace-nowrap text-foreground [&:has([role=checkbox])]:pr-0",
        className
      )}
      {...props}
    />
  )
}

function TableCell({ className, ...props }: React.ComponentProps<"td">) {
  return (
    <td
      data-slot="table-cell"
      className={cn(
        "p-2 align-middle whitespace-nowrap [&:has([role=checkbox])]:pr-0",
        className
      )}
      {...props}
    />
  )
}

function TableCaption({
  className,
  ...props
}: React.ComponentProps<"caption">) {
  return (
    <caption
      data-slot="table-caption"
      className={cn("mt-4 text-sm text-muted-foreground", className)}
      {...props}
    />
  )
}

export {
  Table,
  TableHeader,
  TableBody,
  TableFooter,
  TableHead,
  TableRow,
  TableCell,
  TableCaption,
}
```


---

*Generated 2026-08-23 from the AskBase repository. Regenerate after code changes so this file never drifts from the source.*
