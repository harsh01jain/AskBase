# AskBase (QueryLocal) — Complete Project Explainer

> A study document for interviews. Covers **what** the project does, **how** it does it,
> and **the exact implementation** behind every piece, plus trade-offs, gaps, and a Q&A bank.
>
> Repo layout referenced throughout: `backend/` (FastAPI + Python), `frontend/` (Next.js 14 + TypeScript),
> `docker-compose.yml`, `init.sql`.

---

## Table of Contents

1. [One-line pitch & elevator pitches](#1-one-line-pitch--elevator-pitches)
2. [The problem it solves](#2-the-problem-it-solves)
3. [System architecture](#3-system-architecture)
4. [Tech stack — and why each piece was chosen](#4-tech-stack--and-why-each-piece-was-chosen)
5. [The request lifecycle (the core of the project)](#5-the-request-lifecycle-the-core-of-the-project)
6. [Backend deep dive, file by file](#6-backend-deep-dive-file-by-file)
7. [Frontend deep dive](#7-frontend-deep-dive)
8. [Data model & sample dataset](#8-data-model--sample-dataset)
9. [Security model — defense in depth](#9-security-model--defense-in-depth)
10. [Infrastructure: Docker, env, scripts](#10-infrastructure-docker-env-scripts)
11. [API reference](#11-api-reference)
12. [Key design decisions & trade-offs](#12-key-design-decisions--trade-offs)
13. [Known gaps: where the code differs from the project report](#13-known-gaps-where-the-code-differs-from-the-project-report)
14. [What I would improve next](#14-what-i-would-improve-next)
15. [Interview Q&A bank](#15-interview-qa-bank)
16. [Glossary — terms you must be able to define](#16-glossary--terms-you-must-be-able-to-define)

---

## 1. One-line pitch & elevator pitches

**One line:**
> AskBase is a fully local, privacy-first Text-to-SQL web app: you ask a question in plain English,
> a locally-running LLM writes the PostgreSQL query, the app validates it, runs it read-only, and
> streams back the results, a chart, and a plain-English explanation — with zero data leaving the machine.

**30-second pitch:**
> Business analysts constantly wait on data engineers for simple SQL. Cloud NL-to-SQL tools solve that
> but ship your schema and data to a third party, which regulated industries can't accept. AskBase runs
> the whole pipeline on-premises: Ollama serves a Qwen2.5-Coder model locally, ChromaDB does semantic
> retrieval over the database schema so only relevant tables enter the prompt, sqlglot validates that the
> generated SQL is a pure SELECT, and PostgreSQL executes it under a read-only role with a statement timeout.
> If the query fails, the exact Postgres error is fed back to the model for up to 3 self-correction attempts.
> The Next.js frontend streams progress over Server-Sent Events and renders a table, an auto-generated bar
> chart, a natural-language explanation, and follow-up question suggestions.

**3-minute version (structure to speak to):**
1. Problem → analyst bottleneck + privacy constraint.
2. Architecture → 3 tiers (Next.js UI ↔ FastAPI orchestrator ↔ Postgres + Ollama + ChromaDB).
3. The pipeline → retrieve → generate → validate → execute → self-correct.
4. The three security layers → sqlglot AST check, read-only DB role, statement timeout.
5. The UX layer → SSE streaming, token-by-token explanation, follow-up chips, voice input, audit history.
6. Trade-offs → 7B local model vs GPT-4 accuracy, closed partly by RAG + retry loop.

---

## 2. The problem it solves

**Business problem.** Analysts raise a ticket → wait for a data engineer → get a CSV. That loop takes hours
for questions that are 30 seconds of SQL. Self-service NL-to-SQL removes the queue.

**Why not just use a cloud LLM?** Cloud NL-to-SQL (OpenAI, BigQuery NL mode) sends the **schema** and often
**sample data** to a third-party API. For BFSI / healthcare / government, that's a data-residency violation
(GDPR Art. 25, India's DPDP Act 2023), not merely a preference. AskBase's differentiator is that it is
**private by construction, not by configuration** — there is no cloud code path at all.

**Positioning statement to use in interviews:**
> "The right comparison isn't 'is it as accurate as GPT-4'. It's 'this is the only on-prem NL-to-SQL tool
> with a real web UI, semantic schema retrieval, and hard SQL guardrails that a compliance officer would sign off on.'"

---

## 3. System architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│                          Browser (localhost:3000)                        │
│  Next.js 14 App Router · TypeScript · Tailwind · Recharts · next-themes   │
│  - chat UI, SQL block, results table, bar chart, follow-up chips          │
│  - Web Speech API voice input, dark/light theme                           │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │  fetch() + ReadableStream reader
                             │  POST /query  → text/event-stream (SSE)
                             ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                    FastAPI backend (localhost:8000)                      │
│                              main.py                                     │
│   ┌───────────────┐  ┌──────────────┐  ┌───────────────┐  ┌───────────┐  │
│   │ retrieval.py  │→ │   llm.py     │→ │ validate_sql  │→ │database.py│  │
│   │ ChromaDB RAG  │  │ Ollama HTTP  │  │  sqlglot AST  │  │ psycopg2  │  │
│   └───────────────┘  └──────────────┘  └───────────────┘  └───────────┘  │
│                        ▲──── self-correction loop (max 3) ────┘          │
└───────┬──────────────────────────┬───────────────────────────┬───────────┘
        │                          │                           │
        ▼                          ▼                           ▼
┌────────────────┐      ┌────────────────────┐      ┌─────────────────────┐
│ ChromaDB       │      │ Ollama             │      │ PostgreSQL 15       │
│ ./schema_index │      │ :11434             │      │ :5433 (Docker)      │
│ all-MiniLM-L6  │      │ qwen2.5-coder:7b   │      │ role: nl2sql_reader │
│ (on disk)      │      │ (on host GPU/CPU)  │      │ SELECT-only         │
└────────────────┘      └────────────────────┘      └─────────────────────┘
```

**Three "brains" the backend talks to:**
- **ChromaDB** — vector store of table descriptions; answers "which tables matter for this question?"
- **Ollama** — local LLM server; answers "what SQL answers this question?"
- **PostgreSQL** — the actual data; answers the question.

---

## 4. Tech stack — and why each piece was chosen

| Layer | Technology | Why this one (the interview answer) |
|---|---|---|
| Frontend | **Next.js 14 (App Router) + TypeScript** | Type safety across the API boundary; App Router for a single-page chat shell; standard Node deployment. |
| Styling | **Tailwind CSS + CSS variables + shadcn/ui** | Design tokens in `globals.css` drive light/dark theming with no duplicated styles. |
| Charts | **Recharts** | Declarative React charting; the app infers x/y axes from result columns automatically. |
| Theme | **next-themes** | `attribute="class"`, `defaultTheme="dark"`, `enableSystem` — respects OS preference, persists choice. |
| Backend | **FastAPI + Python 3.11** | Native async, `StreamingResponse` for SSE, Pydantic request validation, auto OpenAPI docs. |
| Streaming | **Server-Sent Events (SSE)** | One-way server→client streaming; simpler than WebSockets, plain HTTP, ideal for token streaming. |
| LLM serving | **Ollama** running `qwen2.5-coder:7b` | Native Windows installer (no WSL2/CUDA toolkit), simple `/api/generate` REST API, code-specialised model. |
| Embeddings | **sentence-transformers `all-MiniLM-L6-v2`** | 384-dim, ~22M params, runs on CPU in milliseconds, strong quality-per-cost for short schema strings. |
| Vector DB | **ChromaDB PersistentClient** | Embedded (no server process), persists to `./schema_index`, telemetry disabled. |
| SQL safety | **sqlglot** | A real SQL **parser** producing an AST — you check the statement *type*, not a regex on a string. |
| Database | **PostgreSQL 15** | `information_schema` for reflection, role-level privileges, `statement_timeout`. |
| DB driver | **psycopg2** with `RealDictCursor` | Returns rows as dicts → serialises straight to JSON for the frontend. |
| HTTP clients | **requests** (sync) + **httpx** (async streaming) | `requests` for the blocking SQL-generation call; `httpx.AsyncClient.stream` for token-by-token explanation. |
| Packaging | **Docker Compose** | postgres + backend + frontend on one private bridge network; Ollama stays on the host via `host.docker.internal`. |

---

## 5. The request lifecycle (the core of the project)

This is the part interviewers dig into. Know it cold. Source: `backend/main.py` → `process_query()`.

### Stage 0 — Request arrives
```python
class QueryRequest(BaseModel):
    question: str
    history: list[dict] = []     # prior {question, sql} pairs for conversational context
```
FastAPI returns a `StreamingResponse(event_stream(), media_type="text/event-stream")`.
Everything below happens **inside an async generator**, so each `yield` flushes to the browser immediately.

### Stage 1 — Schema retrieval (RAG)
```python
yield status "Retrieving schema context..."
context = retrieve_context(question, top_k=5)
```
- The question text is embedded by `all-MiniLM-L6-v2`.
- ChromaDB does an approximate nearest-neighbour search over stored table-description embeddings.
- Returns the top 5 table description strings, e.g.
  `"Table: orders. Columns: order_id (integer), customer_id (integer), order_date (date), total_amount (numeric), status (character varying)"`

**Why RAG here?** Naively pasting a 100-table schema into the prompt blows the context window, costs latency,
and *hurts* accuracy (the model gets distracted by irrelevant tables). Retrieval keeps the prompt small and
relevant, and means the design scales to large databases without change.

### Stage 2 — SQL generation (attempt N)
```python
sql = generate_sql(question, context, history=req.history, error_context=error_msg)
```
The prompt is assembled in `llm.py` from four blocks:
1. **Role + hard rules** — "You are a PostgreSQL expert… only use listed tables/columns, don't invent names,
   map concepts to columns, always use `ILIKE` for string comparisons."
2. **Schema context** — the retrieved table descriptions.
3. **Chat history** — the last 3 `(question, sql)` pairs, so follow-ups like "now only for 2023" work.
4. **Error context** — on retries, the verbatim Postgres error from the previous attempt.

Then: `"Respond ONLY with the raw SQL query, no markdown formatting, no explanation."`
A post-processing step strips ```` ```sql ```` fences anyway, because models ignore that instruction often enough to matter.

The call is `POST {OLLAMA_BASE_URL}/api/generate` with `stream: False`, 30 s timeout.

### Stage 3 — Validation (the safety gate)
```python
def validate_sql(sql: str) -> bool:
    parsed = sqlglot.parse(sql, read="postgres")   # → list of AST root nodes
    if not parsed: return False
    for node in parsed:
        if not isinstance(node, sqlglot.exp.Select):
            return False
    return True
```
Three things this buys you:
- **Type check, not string check.** `INSERT`/`UPDATE`/`DELETE`/`DROP`/`ALTER` parse into different AST classes and are rejected.
- **Multi-statement injection defence.** `sqlglot.parse` returns a *list*; `SELECT 1; DROP TABLE customers;`
  produces `[Select, Drop]` → the loop rejects it.
- **Syntax check for free.** Malformed SQL throws during parse → rejected before touching the database.

If validation fails, the error string becomes `error_context` and the loop retries.

### Stage 4 — Execution
```python
result = execute_query(sql)   # database.py
```
- Opens a fresh connection as `nl2sql_reader` (`connect_timeout=5`).
- Sets `statement_timeout = 15000` ms and `idle_in_transaction_session_timeout = 30000` ms on the session.
- Executes with a `RealDictCursor`, then `cur.fetchmany(1000)` — a 1000-row cap on what's returned.
- Returns `{"columns": [...], "rows": [...]}` on success, or `{"error": "<postgres message>"}` on failure.

### Stage 5 — Self-correction loop
```python
while attempt < max_attempts:      # max_attempts = 3
    attempt += 1
    sql = generate_sql(..., error_context=error_msg)
    if not validate_sql(sql):  error_msg = "Validation Error: ..."; continue
    result = execute_query(sql)
    if "error" in result:      error_msg = result["error"];         continue
    success = True; break
```
**Why this matters conceptually:** a Postgres error message is *extremely* informative context —
`column "revenue" does not exist` tells the model exactly what to fix. This retry loop is the single biggest
accuracy lever in the project: it lets a 7B local model recover from mistakes a 7B model reliably makes,
narrowing the gap to a much larger cloud model. It's capped at 3 to bound worst-case latency.

### Stage 6 — Audit logging
```python
latency_ms = int((time.time() - start_time) * 1000)
insert_audit_log(question, sql, attempt, latency_ms, "Success" | "Failed")
```
Every request — success or failure — is written to a `query_audit` table. That gives you an audit trail for
compliance **and** a metrics table for regression tracking (retry rate, P95 latency per model version).

### Stage 7 — Streaming the response
The SSE stream emits typed JSON events, each framed as `data: {...}\n\n`:

| `type` | Payload | Purpose |
|---|---|---|
| `status` | `message` | Progress text ("Generating SQL (Attempt 2)…") |
| `result` | `sql`, `results`, `attempts`, `latency_ms` | The main payload |
| `explanation_token` | `token` | One token of the plain-English explanation |
| `suggestions` | `data: string[]` | 3 follow-up questions |
| `error` | `sql`, `error`, `attempts` | All attempts failed |
| `done` | — | Stream complete |

**Concurrency detail worth mentioning:** suggestions are kicked off as a background task *before* the
explanation starts streaming, then awaited with a timeout:
```python
suggestions_task = asyncio.create_task(generate_suggestions(question, sql))
async for token in stream_explanation(question, sql):
    yield explanation_token
suggestions = await asyncio.wait_for(suggestions_task, timeout=8.0)
```
So two LLM calls overlap instead of running back-to-back, and a slow suggestions call can't hang the response.

**Serialization detail:** results contain `datetime.date` and `Decimal` values that `json.dumps` can't handle.
`fastapi.encoders.jsonable_encoder` is applied to the payload first to convert them (dates → ISO strings,
Decimals → numbers). `backend/test_encoder.py` exists specifically because this broke once.

---

## 6. Backend deep dive, file by file

### `backend/main.py` — API surface + orchestration
- Creates the FastAPI app and adds permissive **CORS** (`allow_origins=["*"]`) so `localhost:3000` can call `:8000`.
- Endpoints: `/health`, `/schema`, `/history`, `/reindex`, `/query`.
- `/health` checks both dependencies: opens a DB connection, and GETs the Ollama base URL with a 2 s timeout.
- Holds `validate_sql()` and the whole `event_stream()` pipeline described above.

### `backend/database.py` — connections, reflection, audit
Two distinct connection identities, and knowing why is a good interview point:

| Function | Role used | Purpose |
|---|---|---|
| `get_db_connection()` | `nl2sql_reader` (SELECT-only) | Runs all LLM-generated SQL |
| `get_admin_connection()` | `root` (admin) | Creates and writes the `query_audit` table only |

The audit table needs INSERT, and the query role must never have INSERT — so the app holds two credentials and
uses the privileged one only for a fixed, parameterised statement it wrote itself. No LLM output ever touches
the admin connection.

**Schema reflection** (`get_schema_definitions`):
```sql
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public';
```
Rows are grouped by table and flattened into one natural-language sentence per table:
`"Table: customers. Columns: customer_id (integer), name (character varying), segment (character varying), ..."`

**Why a sentence and not JSON?** Because that string is both what gets *embedded* and what gets *pasted into the
prompt*. Natural-language phrasing embeds better against a natural-language question, and reads better to the LLM.

**Audit table**, created at import time via `init_audit_table()`:
```sql
CREATE TABLE IF NOT EXISTS query_audit (
    id SERIAL PRIMARY KEY, question TEXT, generated_sql TEXT,
    attempts INT, latency_ms INT, status VARCHAR(50),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```
`get_audit_history(limit=50)` returns the newest 50, converting `timestamp` to ISO strings for JSON.

### `backend/retrieval.py` — the RAG layer
```python
chroma_client = chromadb.PersistentClient(
    path="./schema_index",
    settings=chromadb.Settings(anonymized_telemetry=False))   # privacy: no phone-home

sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2")
```
- `index_schema()` — pulls schema docs, **deletes and recreates** the collection (simplest way to guarantee
  dropped tables disappear from the index), then `collection.add(documents, metadatas, ids)`.
  The table name is used as the Chroma `id`, so ids are naturally unique and stable.
- `retrieve_context(query, top_k=5)` — `collection.query(query_texts=[query], n_results=top_k)` and returns
  `results['documents'][0]` (the list of matched description strings).

Chroma computes the query embedding using the same embedding function it indexed with — that consistency is
what makes the similarity meaningful.

### `backend/llm.py` — three prompts, three call styles
| Function | Ollama call | Style | Why |
|---|---|---|---|
| `generate_sql()` | `requests.post`, `stream:False` | blocking, full response | You need the complete SQL before validating; you can't validate half a statement. |
| `stream_explanation()` | `httpx.AsyncClient.stream`, `stream:True` | async generator, yields tokens | UX: the explanation types out live instead of appearing after a pause. |
| `generate_suggestions()` | `httpx.AsyncClient.post`, `format:"json"` | async, JSON mode | Ollama's `format: "json"` constrains decoding to valid JSON, so parsing is reliable. |

Defensive parsing in `generate_suggestions`: models sometimes return `{"suggestions": [...]}` instead of a bare
array, so the code checks for a dict, scans its values for the first list, and truncates to 3. Any failure
returns `[]` rather than breaking the stream.

Prompt-engineering choices in `generate_sql` worth defending:
- **"Only use the tables and columns explicitly listed"** — the main hallucination guard.
- **"Always use ILIKE for string comparisons"** — real analysts type "enterprise", the data says "Enterprise".
  Case-insensitive matching prevents silently-empty result sets, which are the worst failure mode
  (it looks like an answer, but it isn't).
- **"If a concept maps to a column, use a WHERE clause"** — teaches concept→column mapping
  ("enterprise customers" → `segment ILIKE '%enterprise%'`).
- **Last 3 history pairs only** — bounded prompt growth; enough for pronoun resolution in follow-ups.

### `backend/seed_db.py` — demo data generator
Creates 4 tables and populates **50 products**, **1,000 customers**, **5,000 orders**, and 1–5 order_items per
order (≈15,000 rows). Uses `TRUNCATE ... RESTART IDENTITY CASCADE` for idempotent re-seeding, `executemany` for
bulk inserts, and weighted random statuses (`Completed` 70%, `Pending` 20%, `Cancelled` 5%, `Refunded` 5%) so
aggregate queries return realistic-looking distributions. Order totals are computed from the actual item rows,
so `orders.total_amount` reconciles with `order_items` — meaning join queries give consistent answers during demos.

### Utility scripts
`test_conn.py` (connection/role password repair), `test_api.py`, `test_history.py`, `test_openapi.py` (endpoint
smoke checks), `test_encoder.py` (JSON serialization of `date` inside `RealDictRow`), `kill_ports.py` (frees
ports 3000/8000 via psutil). Be honest in interviews: **these are manual smoke-test scripts, not a pytest suite.**

---

## 7. Frontend deep dive

A single main component: `frontend/src/app/page.tsx` (a `"use client"` component). Everything below lives there.

### State model
```ts
messages       // full chat transcript: {role, content, sql, results, explanation, attempts, latency, loading, error}
chatHistory    // compact [{question, sql}] sent back to the API for conversational context
suggestions    // 3 follow-up chips; seeded with defaults, replaced by LLM output
schema         // table list from GET /schema, rendered in the sidebar
history        // GET /history audit rows, shown in a modal
activeTab      // "table" | "chart"
```

### SSE consumption — hand-rolled, and there's a reason
The browser's built-in `EventSource` API **only supports GET**. This endpoint is a `POST` with a JSON body,
so the code uses `fetch` + the streaming `ReadableStream` reader and parses the SSE framing manually:
```ts
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
    if (line.startsWith("data: ")) { /* JSON.parse(line.substring(6)) → switch on data.type */ }
    boundary = buffer.indexOf("\n\n");
  }
}
```
Two subtleties to be able to explain:
- **The buffer exists because TCP chunks don't align with SSE messages.** One `read()` may deliver half an event
  or three events; you must accumulate and split on the `\n\n` delimiter.
- **`decoder.decode(value, {stream: true})`** keeps multi-byte UTF-8 characters intact across chunk boundaries.

Each parsed event immutably updates the **last** message in `messages` (`const last = {...updated[len-1]}`),
so React re-renders correctly — mutating in place would not trigger an update.

### Auto-charting heuristic
```ts
for (const col of columns) {
  const val = rows[0]?.[col];
  if (typeof val === "number" && !yKey) yKey = col;   // first numeric column → Y axis
  else if (!xKey) xKey = col;                          // first non-numeric column → X axis
}
```
Falls back to `columns[0]`/`columns[1]`, and shows "Not enough numeric data to visualize" if no pair is found.
Simple, but it covers the dominant shape of analytics results: one label column + one measure column.

### Other UI features
- **Voice input** — Web Speech API (`SpeechRecognition` / `webkitSpeechRecognition`) with `interimResults: true`,
  so the textarea fills as you speak. Feature-detected, with an alert if unsupported.
- **Theming** — `next-themes` toggles a `.dark` class; all colors are CSS variables in `globals.css`, so one
  class flip re-themes the app. The palette mirrors ChatGPT's (`#212121` canvas, `#171717` sidebar).
- **Hydration safety** — a `mounted` flag gates theme-dependent icons; `suppressHydrationWarning` on `<html>`.
  Without this, server and client render different icons and React warns.
- **Latency and attempt badges** on the SQL block — surfacing `latency_ms` and `attempts` makes the retry loop
  visible to the user instead of hidden magic.
- **Copy SQL**, **New chat**, **History modal** (click a past question to re-run it), **Enter to send / Shift+Enter for newline**.
- **Trust disclaimer** under the input: "AskBase generates SQL from natural language. Always verify results."
  That line is a deliberate design decision — see §12.7.

---

## 8. Data model & sample dataset

```
customers                       products
─────────                       ────────
customer_id  PK  SERIAL         product_id  PK  SERIAL
name             VARCHAR(100)   name            VARCHAR(100)
email            VARCHAR(100)   category        VARCHAR(50)
segment          VARCHAR(50)    price           DECIMAL(10,2)
signup_date      DATE                  ▲
     │                                 │ N..1
     │ 1..N                            │
     ▼                                 │
orders                          order_items
──────                          ───────────
order_id     PK  SERIAL         order_item_id PK SERIAL
customer_id  FK → customers     order_id      FK → orders
order_date       DATE           product_id    FK → products
total_amount     DECIMAL(10,2)  quantity         INT
status           VARCHAR(20)    unit_price       DECIMAL(10,2)
     │                                 ▲
     └───────────── 1..N ──────────────┘

query_audit  (created by the app, written via the admin role)
───────────
id PK · question · generated_sql · attempts · latency_ms · status · timestamp
```
Segments: `Enterprise`, `SMB`, `Startup`, `Mid-Market`. Categories: `Software`, `Hardware`, `Services`, `Consulting`.
Date range: 2021-01-01 → 2024-01-01.

This is a deliberately classic e-commerce schema: it exercises single-table filters, joins, `GROUP BY`
aggregation, and date arithmetic — the three difficulty tiers you'd evaluate a text-to-SQL system on.

---

## 9. Security model — defense in depth

The core claim: **even if the LLM is fully compromised or hallucinates a `DROP TABLE`, nothing bad happens.**
Four independent layers, each of which alone would be insufficient:

| # | Layer | Mechanism | Stops |
|---|---|---|---|
| 1 | **Application validation** | `sqlglot` parses to an AST; every root node must be `exp.Select` | DDL/DML, multi-statement injection, malformed SQL |
| 2 | **Database privileges** | `nl2sql_reader` has only `CONNECT`, `USAGE`, `SELECT`; `ALTER DEFAULT PRIVILEGES` extends SELECT to future tables | Any write, even if layer 1 were bypassed |
| 3 | **Resource limits** | `statement_timeout = 15s`, `idle_in_transaction_session_timeout = 30s`, set at both role level (`init.sql`) and per session | Runaway cartesian joins, connection exhaustion |
| 4 | **Result cap** | `cur.fetchmany(1000)` | Dumping a million-row table into the browser |

**Privacy layers (NFR-01):**
- Ollama inference runs entirely on `localhost:11434` — no API key, no outbound call.
- sentence-transformers downloads the embedding model once, then runs CPU-local forever.
- ChromaDB is an embedded persistent client writing to local disk, with `anonymized_telemetry=False`.
- After first-run downloads, the whole system works **fully offline**.

**Least privilege in one sentence:** the role that executes untrusted (LLM-generated) SQL is a different,
strictly weaker role than the one that writes the audit log.

**Honest weaknesses to volunteer if asked** (see §13): CORS is `["*"]`, there is no authentication layer, and
admin DB credentials live in environment variables. All are acceptable for a localhost / private-network
deployment, and all are the first things to fix before a multi-user rollout.

---

## 10. Infrastructure: Docker, env, scripts

### `init.sql` — runs once on first Postgres container start
```sql
CREATE ROLE nl2sql_reader WITH LOGIN PASSWORD 'yourpassword';
GRANT CONNECT ON DATABASE yourdatabase TO nl2sql_reader;
GRANT USAGE ON SCHEMA public TO nl2sql_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO nl2sql_reader;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO nl2sql_reader;
ALTER ROLE nl2sql_reader SET statement_timeout = '15s';
ALTER ROLE nl2sql_reader SET idle_in_transaction_session_timeout = '30s';
```
`ALTER DEFAULT PRIVILEGES` is the important line: without it, every newly created table would be invisible to
the reader role and you'd have to re-`GRANT` manually. Role-level `SET` means the timeouts survive application
restarts and misconfiguration.

### `docker-compose.yml` — 3 services on a private bridge network
- **postgres**: `postgres:15`, host port **5433** → container 5432 (5433 avoids clashing with a locally installed
  Postgres), named volume `pgdata`, `init.sql` mounted into `/docker-entrypoint-initdb.d/`.
- **backend**: built from `backend/Dockerfile` (python:3.11-slim + gcc/libpq for psycopg2), port 8000.
  Inside Docker it reaches the DB by service name (`POSTGRES_HOST=postgres`, port 5432) and reaches
  **Ollama on the host** via `host.docker.internal` + `extra_hosts: host-gateway`.
- **frontend**: built from `frontend/Dockerfile`, port 3000.

**Why Ollama stays on the host and isn't containerised:** GPU passthrough into a container needs the NVIDIA
Container Toolkit and is fragile on Windows; the host-installed Ollama already has GPU acceleration and its
model cache. `host.docker.internal` bridges the two cleanly.

### Environment variables
`backend/.env`: `POSTGRES_USER/PASSWORD/HOST/PORT/DB`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`
(plus `POSTGRES_ADMIN_USER/PASSWORD`, read in `database.py`).
Root `.env`: `OLLAMA_MODEL` for compose interpolation.

### Convenience scripts
`start.bat` / `start.sh` (bring up the whole stack), `kill_ports.bat` / `kill_ports.py` (free ports 3000/8000).

---

## 11. API reference

| Method | Path | Returns |
|---|---|---|
| `GET` | `/health` | `{"database": "ok"\|"error", "ollama": "ok"\|"error"}` |
| `GET` | `/schema` | `[{"table": "...", "description": "Table: ... Columns: ..."}]` |
| `GET` | `/history` | Last 50 `query_audit` rows, newest first |
| `POST` | `/reindex` | `{"status": "success", "tables_indexed": N}` |
| `POST` | `/query` | `text/event-stream` — typed SSE events (see §5, Stage 7) |

Request body for `/query`:
```json
{ "question": "Show me the top 5 customers by revenue",
  "history": [{"question": "...", "sql": "..."}] }
```

---

## 12. Key design decisions & trade-offs

Each of these is a "why did you do it that way?" question waiting to happen.

**1. RAG over the schema instead of dumping the whole schema.**
Trade-off: retrieval can *miss* a needed table (a recall failure), producing a wrong query.
Justification: prompt size stays constant as the database grows, latency stays low, and accuracy improves
because irrelevant tables don't distract the model. `top_k=5` is the tuning knob.

**2. sqlglot AST validation instead of regex blocklists.**
A regex like `/drop|delete/i` is trivially bypassed (comments, casing, nested statements) and produces false
positives (a column literally named "deleted"). Parsing to an AST and asserting the node type is categorical,
not heuristic.

**3. Self-correction loop capped at 3.**
Trade-off: worst case is 3× the latency. Justification: each attempt carries the exact DB error, so success
probability rises steeply on attempt 2; beyond 3, models tend to loop on the same mistake, so more retries buy
latency but not accuracy.

**4. SSE instead of WebSockets.**
The data flow is strictly server→client during a query. SSE is plain HTTP (no upgrade handshake, no extra
infrastructure), auto-reconnects, and is trivially proxied. WebSockets would be over-engineering.

**5. Non-streaming SQL generation, streaming explanation.**
You cannot validate a half-written SQL statement, so SQL is generated in full. The *explanation* has no
correctness gate, so streaming it token-by-token is pure UX win — perceived latency drops even though total
time is unchanged.

**6. A 7B model, not 32B, as the default.**
Fits in 8 GB VRAM and runs on CPU. The RAG + retry loop is explicitly the compensation for the smaller model.
The model is one env var (`OLLAMA_MODEL`), so upgrading to `:14b` or `:32b` on better hardware is a one-line change.

**7. Always show the generated SQL.**
The dangerous failure mode in text-to-SQL is not an error — it's a query that runs cleanly and answers a
*subtly different question*. No validator catches that. Showing the SQL plus a plain-English explanation makes
the system auditable by the human, which is also why the disclaimer line exists.

**8. Two database roles.**
Audit logging needs INSERT; the query path must never have it. Splitting identities keeps the least-privilege
property intact rather than weakening the reader role for convenience.

**9. Web app, not a desktop/Streamlit app.**
One GPU server serves the whole analyst team; updates deploy once; no per-laptop install. Privacy is preserved
because it's hosted on the private network, not the public internet.

---

## 13. Known gaps: where the code differs from the project report

**Say these before an interviewer finds them — it reads as engineering maturity, not weakness.**
The original report (`project_docs.txt`) was written at planning stage and describes some things the shipped
code doesn't do:

| Report claims | Actual code | Note |
|---|---|---|
| "1000-row `LIMIT` injected into the SQL" | `cur.fetchmany(1000)` — capped **client-side** | Postgres still computes the full result set, and psycopg2's default cursor buffers it. Real fix: inject `LIMIT` into the AST with sqlglot, or use a server-side named cursor. |
| Prompts stored in `/prompts/` templates; model read from `config.yaml` | Prompts are f-strings in `llm.py`; model comes from an env var | The env var still gives model hot-swap without code changes. |
| Startup health gate returns 503 if Ollama is down | `/health` exists, but there's no startup gate | |
| Backend auto-indexes schema on startup (README) | No startup event calls `index_schema()`; you must `POST /reindex` | Worth fixing — it's a two-line `@app.on_event("startup")`. |
| Editable SQL field on final failure | The error and last SQL are displayed, not editable | |
| 4 follow-up suggestions | 3 | |
| Schema panel highlights tables used in the current query | Sidebar lists tables and expands to show columns | |
| SQL streams token-by-token to the UI | Only the *explanation* streams; SQL arrives complete | Intentional — see §12.5. |
| Ollama runs as a Docker service with GPU passthrough | Ollama runs on the host, reached via `host.docker.internal` | Intentional — see §10. |
| Gold-set regression suite / evaluation harness | Not implemented | The biggest genuine gap. |

**Other real limitations in the current code:**
- `validate_sql` accepts only `exp.Select` root nodes, so a `UNION` query (which parses as `exp.Union`) is
  rejected even though it's read-only. CTEs (`WITH ... SELECT`) are fine, because sqlglot attaches them to the Select node.
- `generate_sql` uses a **blocking `requests.post` inside an async endpoint** — it blocks the event loop for
  the duration of inference, so concurrent users serialise. Fix: `httpx.AsyncClient` or `run_in_threadpool`.
- The frontend hardcodes `http://localhost:8000` even though compose passes `NEXT_PUBLIC_API_URL`.
- `CORS allow_origins=["*"]` — fine on localhost, wrong for a network deployment.
- No authentication/authorisation layer, no per-user row-level security.
- No automated tests; the `test_*.py` files are manual smoke scripts.
- Each query opens a **new database connection** — no pooling (`psycopg2.pool` or PgBouncer would fix it).
- Reindexing deletes and recreates the whole Chroma collection rather than upserting deltas.

---

## 14. What I would improve next

Ordered the way you'd actually prioritise them:

1. **Evaluation harness** — 30–50 gold `(question, SQL)` pairs; compare *executed result sets* as sorted
   DataFrames, not SQL strings (many correct queries are textually different). Track execution accuracy,
   retry-rate distribution, and P95 latency; gate model/prompt changes on a >5% regression.
2. **Real `LIMIT` injection** — rewrite the AST with sqlglot to append or clamp a `LIMIT`, instead of capping client-side.
3. **Async LLM calls + connection pooling** — remove the blocking `requests` call; add `psycopg2.pool`.
4. **Auth + tightened CORS** — Next.js middleware with JWT, an origin allowlist, per-user audit attribution.
5. **Auto-reindex on startup, plus schema-change detection.**
6. **Richer schema context** — foreign-key relationships, column comments, and a few sample values per column.
   FK knowledge is the single biggest driver of correct JOINs.
7. **Few-shot examples in the prompt** — retrieve similar previously-successful `(question, SQL)` pairs from the
   audit table and include them. That turns the audit log into a self-improving example store.
8. **Result caching** — hash (question + schema version) → cached SQL, to skip inference on repeat questions.

---

## 15. Interview Q&A bank

**Q: Walk me through what happens when I type a question.**
See §5. Hit the five stages by name: retrieve → generate → validate → execute → self-correct, then streaming.

**Q: How do you stop the LLM from dropping a table?**
Four independent layers (§9). Lead with: "the validator parses to an AST and requires every root node to be a
SELECT — which also kills multi-statement injection, because `sqlglot.parse` returns a list. And even if that
failed, the database role has no write grants at all."

**Q: Why RAG for the schema? Why not just paste the whole thing?**
Prompt size, latency, and accuracy — irrelevant tables actively degrade generation quality. It also means the
design scales to a 100-table database unchanged. The cost is retrieval recall failures, mitigated by `top_k`.

**Q: What is an embedding, concretely, in your project?**
A 384-dimensional vector produced by `all-MiniLM-L6-v2` from a table's description sentence. Semantically
similar text lands close together in that space, so similarity between the question's vector and each table's
vector ranks tables by relevance.

**Q: Why ChromaDB and not FAISS or pgvector?**
Chroma is embedded (no server process), persists to disk, and bundles the embedding function so index-time and
query-time embeddings can't drift apart. pgvector would be the natural upgrade if I wanted the vectors inside
the same Postgres instance; FAISS if I needed raw ANN performance at much larger scale.

**Q: Why SSE and not WebSockets?**
One-directional server→client streaming over plain HTTP. No handshake, no extra infrastructure, built-in
reconnect. WebSockets solve bidirectional messaging, which this doesn't need.

**Q: Why did you hand-roll the SSE parser instead of using `EventSource`?**
`EventSource` is GET-only; `/query` is a POST with a JSON body. So I read the `ReadableStream` and split on
`\n\n` myself, buffering across chunks because TCP boundaries don't align with SSE message boundaries.

**Q: How does the self-correction loop actually help?**
The Postgres error message is high-signal context. `column "revenue" does not exist` names the exact mistake,
so attempt 2 has strictly more information than attempt 1. It's the mechanism that lets a 7B model perform
closer to a much larger one. Capped at 3 because returns diminish sharply and latency has to be bounded.

**Q: What's the hardest failure mode?**
A query that executes successfully but answers a subtly different question — wrong JOIN condition, missing
WHERE filter, aggregation on the wrong column. No automated layer catches it. That's why the SQL and its
plain-English explanation are always shown, and why the disclaimer sits under the input box.

**Q: How would you measure whether this works?**
Execution accuracy against a gold set, comparing result sets rather than SQL strings; retry-rate distribution;
P50/P95 latency; and a failure taxonomy (join errors vs filter errors vs hallucinated columns). Every request
already logs question, SQL, attempts, latency, and status to `query_audit`, so the data collection is in place.

**Q: How does conversational context work?**
The frontend keeps a compact `chatHistory` of `{question, sql}` pairs and posts it with each request. The
backend injects the last 3 into the prompt under a `PREVIOUS CHAT HISTORY` header, so "now only for 2023"
resolves against the previous SQL. Bounded at 3 to keep the prompt small.

**Q: What are the two Postgres roles for?**
`nl2sql_reader` executes LLM SQL and has only SELECT. `root` writes the audit table. Splitting them preserves
least privilege — the untrusted path never has write access.

**Q: What would break first under load?**
`generate_sql` uses a blocking `requests.post` inside an async endpoint, so it holds the event loop and
concurrent requests serialise. Also, every query opens a fresh DB connection. Fixes: an async HTTP client,
connection pooling, and swapping Ollama for vLLM for batched concurrent inference.

**Q: Why a local 7B model instead of GPT-4?**
Compliance, cost, and offline operation. The accuracy gap is real, and I compensate with schema RAG and the
retry loop. The model name is an env var, so upgrading to `qwen2.5-coder:32b` on better hardware is a one-line change.

**Q: What did you learn?**
Guardrails matter more than model size for this class of problem; a parser beats a regex every time; and
streaming is mostly a *perceived*-latency optimisation, not a real one — but perceived latency is what users experience.

---

## 16. Glossary — terms you must be able to define

- **Text-to-SQL / NL2SQL** — translating a natural-language question into an executable SQL query.
- **RAG (Retrieval-Augmented Generation)** — retrieve relevant context from a knowledge store and inject it into
  the prompt, instead of relying on the model's parameters. Here the "knowledge" is the database schema.
- **Embedding** — a dense vector representation of text where semantic similarity ≈ geometric closeness.
- **Vector database** — stores embeddings and answers approximate nearest-neighbour queries.
- **`all-MiniLM-L6-v2`** — a small sentence-transformer producing 384-dim embeddings; fast enough for CPU.
- **AST (Abstract Syntax Tree)** — the parsed tree structure of code. sqlglot produces one; the validator checks
  the root node's *type*.
- **SSE (Server-Sent Events)** — HTTP streaming of `data: ...\n\n` frames, server→client only.
- **`statement_timeout`** — a Postgres setting that aborts any query exceeding a duration.
- **Least privilege** — grant exactly the permissions needed, nothing more.
- **Self-correction / error-feedback loop** — feeding a failed execution's error back into the model to regenerate.
- **Ollama** — a local LLM server exposing a REST API (`/api/generate`) over quantised GGUF models.
- **Qwen2.5-Coder** — Alibaba's code-specialised LLM family; strong at SQL for its parameter count.
- **Quantisation (Q4)** — compressing model weights to 4 bits to fit in less VRAM, trading a little accuracy for size and speed.
- **`information_schema`** — the SQL-standard set of views describing a database's own tables and columns.
- **Idempotent seeding** — `TRUNCATE ... RESTART IDENTITY CASCADE`, so re-running the seeder gives the same state.
- **Hydration mismatch** — a React error when server-rendered HTML differs from the client's first render;
  handled here with a `mounted` flag and `suppressHydrationWarning`.

---

## Quick facts cheat sheet

| | |
|---|---|
| Project name | AskBase (originally QueryLocal) |
| Model | `qwen2.5-coder:7b` via Ollama on `:11434` |
| Embedding model | `all-MiniLM-L6-v2` (384-dim, sentence-transformers) |
| Vector store | ChromaDB PersistentClient → `backend/schema_index/` |
| Database | PostgreSQL 15 on host port **5433**, role `nl2sql_reader` |
| Backend | FastAPI on `:8000` |
| Frontend | Next.js 14 on `:3000` |
| Max retries | 3 |
| Retrieval top_k | 5 tables |
| Row cap | 1000 (`fetchmany`) |
| Statement timeout | 15 s (role + session level) |
| Idle transaction timeout | 30 s |
| Seeded data | 1,000 customers · 50 products · 5,000 orders · ~15,000 order items |
| Suggestions timeout | 8 s |
