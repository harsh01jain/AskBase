You are a senior presentation designer and a Python engineer. Build me a 10-slide PowerPoint deck.

Deliver it as **a single complete `python-pptx` script that you execute**, then give me the resulting `.pptx` file. Do not describe the deck — build it. If you cannot execute code, output the full script and nothing else.

---

# 1. WHAT THIS DECK IS FOR

An MSc Data Science project defence at NMIMS, worth 20 marks, presented in 7–10 minutes by Harsh Jain.

The marking rubric requires the deck to cover:

1. **Application need**
2. **Development approach and features**
3. **Challenges faced (technical and otherwise)**
4. **Limitations and future scope**

Every slide below maps to one of those four. Do not add slides. Do not drop slides.

---

# 2. DESIGN SYSTEM — FOLLOW THIS EXACTLY

Pick **Theme A** unless I say otherwise. Use exactly one theme; never mix.

### Theme A — Editorial White (default, recommended)

Reads as a premium printed report. Projects well in a bright classroom.

| Token | Hex | Use |
|---|---|---|
| `CANVAS` | `FFFFFF` | slide background |
| `PANEL` | `F5F6F8` | card / panel fill |
| `PANEL_ALT` | `ECEEF2` | alternating rows, secondary panels |
| `INK` | `0B0F19` | headings, card titles |
| `BODY` | `4B5563` | body text |
| `MUTED` | `9AA3AF` | eyebrows, captions, page numbers |
| `RULE` | `E4E7EB` | borders, hairlines |
| `ACCENT` | `4338CA` | the single accent (indigo) |
| `ACCENT_SOFT` | `EEF0FD` | accent-tinted fill |
| `CAUTION` | `B45309` | used ONLY on the limitations slide |

Type: **Georgia** for slide titles and big numbers. **Calibri** for everything else. **Consolas** for technical values only.

### Theme B — Swiss Technical

Pure white, no filled cards at all — structure comes from hairline rules and the grid. `CANVAS FFFFFF`, `INK 000000`, `BODY 3A3A3A`, `RULE DADADA`, `ACCENT E5341C` (vermilion). Everything Arial. Labels are small-caps, 9pt, letter-spaced 1.5. Maximum whitespace. Use only when you want the deck to feel like a design studio artefact.

### Theme C — Graphite Dark

`CANVAS 0E1116`, `PANEL 171B22`, `INK F5F7FA`, `BODY A2ABB8`, `MUTED 6B7686`, `RULE 262C36`, `ACCENT 7C5CFF` (violet). Same typography as Theme A. Use only if I ask for dark.

### Type scale — do not deviate

| Element | Size | Weight |
|---|---|---|
| Eyebrow / section label | 10pt | bold, letterspacing 2, `ACCENT` |
| Slide title | 34pt | bold, `INK` |
| Big number / stat | 44–60pt | bold, `ACCENT` |
| Card title | 15pt | bold, `INK` |
| Body / card text | 11.5pt | regular, `BODY` |
| Node label in a diagram | 10.5pt | regular |
| Technical value | 9.5pt | Consolas, `ACCENT` |
| Page number / footer | 9pt | `MUTED` |

### Geometry

- Slide: **13.333in × 7.5in** (16:9).
- Outer margin **0.65in** on all sides. Content width **12.03in**. Nothing may sit closer than 0.55in to any edge.
- Title block: eyebrow at y=0.52, title at y=0.80. Body content starts at y≥1.6.
- Footer baseline at y=6.98. **All content must end by y=6.75.**
- Gutter between cards in a row: **0.25in**. Cards in the same row must share identical y and height.
- Corner radius: 0.04in on panels. Never larger.

---

# 3. HARD RULES

**Never:**
- Gradients, drop shadows, glows, 3-D effects, or bevels. In `python-pptx` you must explicitly call `shape.shadow.inherit = False` on **every** shape, or PowerPoint applies an ugly default shadow.
- Emoji, clipart, stock icons, or WordArt.
- A coloured bar or stripe under a slide title, or down the edge of a slide or card. This is the single clearest tell of a generated deck.
- Centred body text or centred paragraphs. Centre only short labels inside diagram nodes and single-line callout banners.
- More than one accent colour. `CAUTION` appears on one slide only.
- Text that overflows its shape, or two shapes that overlap.
- Paragraphs. No sentence longer than ~18 words.

**Always:**
- **One idea per slide.** The title states that idea as a claim, not a category. "Why AskBase?" beats "Introduction".
- **Maximum 70 words per slide**, counting every heading, label and caption. Diagram slides should land near 50.
- Left-align all text blocks. Set text frame margins to 0 so text aligns with the shapes beside it.
- Accent colour on **under 10%** of the slide. It marks one thing: the thing you want looked at first.
- Consistent vertical rhythm — pick 0.25in or 0.4in for gaps and reuse it.
- Real whitespace. If a slide feels empty, that is correct; do not fill it.

---

# 4. LAYOUT PATTERNS — BUILD DIAGRAMS, NOT BULLET LISTS

At most **two** slides may use a plain card grid. Every other slide uses one of these:

1. **Horizontal pipeline** — N equal nodes in a row, connected by a small "→" glyph in `ACCENT` centred in each gap. First and last node styled differently (`ACCENT_SOFT` fill) to mark input and output.
2. **Layered stack** — full-width horizontal bands stacked vertically, joined by a centred "↓" glyph. Used for architecture.
3. **Return / feedback arrow** — a left-pointing arrow shape running back underneath a pipeline, with its label centred on the shaft. Used for retry loops.
4. **Two-column comparison** — two panels side by side, each containing a vertical chain of nodes joined by "↓". End each column with a single bold outcome word.
5. **Nested funnel** — 4 bands, each ~0.9in narrower than the one above and horizontally centred, forming a taper. Used for defence-in-depth. Label each band at the left margin in `MUTED`.
6. **Timeline** — a hairline rule across the top with a small filled dot above each card, cards hanging beneath.
7. **Problem → solution rows** — compact rows: problem in `INK` bold on line 1, then an "→" in `ACCENT` followed by the solution in `BODY` on line 2.

---

# 5. PROJECT FACTS — ACCURATE, DO NOT INVENT

**AskBase** — a fully local, privacy-first Text-to-SQL web application. A user asks a question in plain English; the system retrieves relevant schema, generates PostgreSQL, validates it, executes it read-only, and returns results, the SQL, a chart, an explanation and follow-up suggestions.

**The differentiator: no cloud LLM API. Data, schema, embeddings and inference all stay local. It runs offline after setup.**

Pipeline: retrieve relevant schema by semantic search → send only that schema to a local LLM → generate a PostgreSQL SELECT → validate via AST → execute under a read-only role → on failure, feed the database error back and retry, up to 3 attempts.

| Fact | Value |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Recharts |
| Backend | FastAPI, Python 3.11, Server-Sent Events for streaming |
| Local LLM | Qwen2.5-Coder 7B via Ollama |
| Embeddings | all-MiniLM-L6-v2 (Sentence Transformers) |
| Vector database | ChromaDB |
| Retrieval | top_k = 5 relevant tables |
| Database | PostgreSQL 15, psycopg2 |
| SQL validation | sqlglot AST parsing, SELECT statements only |
| DB access | read-only role |
| Statement timeout | 15 seconds |
| Row cap | 1000 rows |
| Max retry attempts | 3 |
| Deployment | Docker Compose |
| UI features | SQL display, results table, charts, explanations, voice input, query history, follow-up suggestions |

Do not claim any capability not listed here. No invented metrics, accuracy percentages, benchmarks or user numbers.

---

# 6. THE 10 SLIDES

Content is specified below. Keep it this short — tighten wording if you like, never expand it.

**Slide 1 — Title.** `AskBase`. Subtitle: *Privacy-First Natural Language to SQL using Local LLMs*. Eyebrow: MSC DATA SCIENCE · NMIMS. Name: Harsh Jain. Add a small 5-node pipeline strip low on the slide: Natural Language → AI → SQL → Database → Insights. Generous empty space. This slide should feel expensive.

**Slide 2 — Why AskBase?** *(application need)* Two-column comparison. Left "TRADITIONAL DATA ACCESS": Business user → Raises a data request → Waits for analyst → Receives SQL or CSV → end with **Hours to days**. Right "ASKBASE": Business user → Asks in plain English → Results, SQL, chart, explanation → end with **Seconds**. Beneath, four short chips: Slow data access · Dependency on technical teams · Limited self-service analytics · Cloud AI raises privacy concerns.

**Slide 3 — Ask Questions, Get Data.** *(the solution)* One horizontal pipeline: User Question → Semantic Schema Retrieval → Local LLM → Safe SQL → PostgreSQL → Results + Chart + Explanation. Below it three large cards, each a single word with one supporting line: **Private** — everything runs locally. **Simple** — natural language instead of SQL. **Safe** — multiple SQL security layers.

**Slide 4 — System Architecture.** Layered stack, three bands.
Band 1 "USER INTERFACE" — Next.js 14 · TypeScript, with five small chips: Chat, Voice input, SQL display, Results table, Charts.
Band 2 "AI BACKEND" — FastAPI · Python 3.11 · SSE, containing a 4-node pipeline: ChromaDB Retrieval → Local LLM via Ollama → SQL Validation → PostgreSQL Execution. Draw the self-correction loop as a return arrow beneath, labelled "error feedback · max 3 attempts".
Band 3 "CORE SERVICES" — three cards: ChromaDB (vector store · all-MiniLM-L6-v2), Ollama (Qwen2.5-Coder 7B · local inference), PostgreSQL 15 (psycopg2 · read-only role).

**Slide 5 — The Request Lifecycle.** *(development approach — make this the strongest slide)* Six numbered stages in a horizontal pipeline, each with a title, one short line, and a technical value pinned at the card's base:
1 **Ask** — natural language question — `plain English`
2 **Retrieve** — relevant tables via embeddings — `ChromaDB · top_k 5`
3 **Generate** — PostgreSQL query written — `Qwen2.5-Coder 7B`
4 **Validate** — AST parsed, SELECT only — `sqlglot`
5 **Execute** — read-only role runs the query — `15s · 1000 rows`
6 **Correct** — DB error returned to the model — `max 3 attempts`
Add a return arrow from stage 6 back toward stage 3, labelled "on failure, retry with the database error as context", plus a small emphasised block: **Maximum 3 attempts**.

**Slide 6 — What AskBase Delivers.** *(features)* Six cards, each a title plus one line of at most eight words: Natural Language Queries · Semantic Schema Retrieval · Self-Correcting SQL · SQL Safety · Real-Time Experience (SSE) · Data Visualization. Then a row of four small chips: Voice Input · Query History · Follow-up Suggestions · Dark / Light Mode.

**Slide 7 — Privacy and Safety by Design.** Nested funnel, four bands narrowing downward:
Layer 1 **AST Validation** — only SELECT queries accepted
Layer 2 **Read-Only Database Role** — LLM cannot modify data
Layer 3 **Resource Limits** — 15-second query timeout
Layer 4 **Result Protection** — maximum 1000 rows returned
To the right, a panel titled **Fully Local Architecture** with three short points: No external LLM API · No data sent to the cloud · Operates offline after setup.

**Slide 8 — Challenges & How We Solved Them.** Problem → solution rows in two columns.
TECHNICAL: Small LLM hallucinating columns → RAG + strict prompting + error-feedback retries. Streaming POST responses → Fetch + ReadableStream instead of EventSource. DB values not JSON serializable → FastAPI JSON encoding. Local hardware limitations → optimised around a 7B code model.
PRACTICAL: Building trust in AI-generated SQL → show the generated SQL, retry count and latency. Balancing privacy vs model capability → local architecture instead of cloud dependency.

**Slide 9 — Current Limitations.** Subtitle: *Known limitations of the current prototype*. Four cards, `CAUTION` accent, each a title and one line: **Model Size** — 7B may be less accurate than larger cloud models. **Schema Retrieval Risk** — relevant tables can occasionally be missed. **No Authentication** — designed for localhost or private networks. **Limited Evaluation** — no formal benchmark accuracy evaluation yet. Close with a single line: *Each of these is addressed in the roadmap →*

**Slide 10 — Where AskBase Goes Next.** Timeline with five cards: **Larger Local Models** — improve SQL generation accuracy. **Authentication & RBAC** — secure multi-user deployment. **Query Optimization** — better performance and large results. **Benchmark Evaluation** — gold-standard Text-to-SQL dataset. **Enterprise Deployment** — larger schemas and private databases. Then the closing statement, set larger and centred in a single banner: *AskBase transforms natural language into actionable database insights while keeping data private, local, and protected.* Finish with a small **Thank You | Questions?**

---

# 7. SPEAKER NOTES

Add speaker notes to every slide via `slide.notes_slide.notes_text_frame.text`. Two to four sentences each: what to say, what to point at, and what to skip. Written to be spoken aloud, not read off the screen. Total runtime 7–10 minutes.

---

# 8. PYTHON-PPTX REQUIREMENTS

- `prs.slide_width = Inches(13.333)`, `prs.slide_height = Inches(7.5)`. Use the blank layout, `prs.slide_layouts[6]`.
- Paint the background with a full-bleed rectangle, or set the slide background fill explicitly. Never leave it default.
- On **every** shape: `shape.shadow.inherit = False`. Remove borders you don't want with `shape.line.fill.background()`.
- On every text frame: `tf.word_wrap = True`, and set `margin_left/right/top/bottom = 0`.
- Use `MSO_SHAPE.ROUNDED_RECTANGLE` for panels and set `adjustment` small for a subtle radius; `MSO_SHAPE.LEFT_ARROW` for return arrows.
- Build helper functions — `panel()`, `label()`, `pipeline()`, `card()` — and reuse them, so spacing stays identical across slides. Do not hand-place every shape.
- Colours via `RGBColor.from_string("4338CA")`. Positions in `Inches()`, font sizes in `Pt()`.

---

# 9. BEFORE YOU RETURN THE FILE — CHECK

1. Exactly 10 slides.
2. Every slide ≤ 70 words. Count them and tell me the per-slide counts.
3. No shape crosses y = 6.75 or sits within 0.55in of any edge.
4. No text overflows its shape — reduce the shape count or shorten the copy, never the font size below the scale above.
5. Cards in the same row share identical y, height and width.
6. One accent colour only; `CAUTION` on slide 9 only.
7. No shadows anywhere — confirm `shadow.inherit = False` is set on every shape.
8. No claim appears that is not in section 5.

Report the word counts and confirm each check, then give me the file.
