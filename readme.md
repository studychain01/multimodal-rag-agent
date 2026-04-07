# Vulcan OmniPro 220 — Technical Support Agent

A **multimodal RAG support agent** for the Vulcan OmniPro 220 multiprocess welder. Answers are grounded in the real manuals (owner manual, quick-start, selection charts), retrieved from semantically chunked knowledge, and returned as structured UI blocks: **text**, **manual page images**, **Mermaid diagrams**, **inline SVG**, and **interactive React components**.

---

## Why multimodal?

Welding support mixes facts, visuals, and procedures. Users need **what to do next**, **how cables map to polarity**, and **numbers they can set** — not only paragraphs. This stack combines:

1. **Grounded text** — A tool-using agent **searches the knowledge base** before answering (not free recall).
2. **Manual-grounded imagery** — When a factory diagram or photo matters, the UI can show **actual manual pages** (`manual_image` blocks; pixels from the API).
3. **Generated structure** — For troubleshooting flows or simple geometry, the model can emit **Mermaid** or **SVG** the client renders.
4. **Interactive components** — For duty cycle, wire settings, and polarity, **embedded calculators/configurators** collect inputs and reflect doc-driven patterns.

### Output modalities

| Block type | Role | When it helps |
|------------|------|----------------|
| **text** | Primary explanation (required first block) | Every answer; safety notes, specs, step lists |
| **manual_image** | Real PDF page PNGs from the server | Wiring diagrams, photos, tables exactly as in the manual |
| **mermaid** | Flowcharts / decision trees | Troubleshooting (“if porosity, check gas → polarity → …”), branching procedures |
| **svg** | Small custom vector diagrams | Labeled joint types, simple schematics not tied to one manual page |
| **component** | Stateful React UI | Duty cycle calculator, wire/material configurators, polarity/cable helpers |

Together, **manual_image** is retrieval-grounded visuals; **mermaid**, **svg**, and **component** are **model- or tool-orchestrated** modalities that make the same chat surface work for reading, deciding, and configuring.

---

## Knowledge base: chunking strategy

PDFs are rasterized to **per-page PNGs** (200 DPI in `ingest.py`). A **vision model** reads each page and returns **JSON chunks**: header, body text, `has_diagram` / `diagram_description`, tables, and `content_type` (safety, specs, setup, troubleshooting, etc.).

### Single-page extraction

Each page is analyzed alone. The model sets **`is_complete`** when the page ends at a natural boundary; **`false`** when content clearly continues (split table, list, section, or mid-thought).

### Two-page (multi-page) merge

If a run-on section spans **two** pages, both images are sent together so cross-page tables and continued sections become **one chunk** with a correct `pages` list.

### Sliding window (three or more pages)

If a section spans **three or more** pages, a **sliding window** walks the page sequence:

- Default **window size = 3**, **overlap = 1** (step = 2).
- Each window uses a prompt that expects **edge overlap** with neighboring windows.
- Chunks are **deduplicated** via a fingerprint (source + normalized header + content prefix) to limit double-counting.

Chunks are embedded into **ChromaDB** with metadata (source, page range, section, diagram/table flags). The stored text includes **diagram_description** and **table_text** so retrieval stays useful when users describe problems in informal language.

---

## Architecture

| Layer | Stack |
|--------|--------|
| API | FastAPI — `POST /chat`, `GET /page/{source}/{page_num}`, page listing |
| Agent | Claude (tool loop): `search_knowledge_base`, `get_page_image`, `find_relevant_pages`, `emit_component` |
| Memory | In-memory **sessions** with optional **rolling summarization** when message lists grow (see `backend/sessions.py`) |
| RAG | Chroma persistent client (`./knowledge_base`), populated by `backend/ingest.py` |
| UI | React 19 + Vite + Tailwind + Mermaid; block renderer maps types to components |

---

## How the agent works

The chat agent is implemented in **`backend/agent.py`** as a **Claude tool-use loop** (`claude-opus-4-5`, up to **5** tool rounds per user message). It does **not** answer from memory alone: the system prompt requires **searching the manual index first**, then choosing tools and finally returning a single **JSON object** whose `blocks` array the UI renders (text, images, Mermaid, SVG, components). The server **parses** that JSON from the model’s last assistant message.

### How it “thinks” (behavior)

- **Retrieve before claim** — Start with **`search_knowledge_base`** (or related lookup) so specs, safety, and procedures come from ingested chunks, not improvisation.
- **Bounded search** — Prompt caps repeated search (e.g. do not query the same thing twice; limit search calls per answer) so the loop stays focused and cheaper.
- **Tools for facts, blocks for the user** — Tool results are compact (e.g. page checks return which PNGs exist, not image bytes). The final reply is structured **blocks** so the frontend can show diagrams and widgets consistently.
- **Technician tone** — Short, practical answers; one clarifying question if needed; safety without being preachy.

### Tools (`backend/tools.py`)

| Tool | What it does |
|------|----------------|
| **`search_knowledge_base`** | Semantic search over Chroma chunks (optional `content_type` filter, `n_results`). **Call first** for almost every user question. Returns text, source, pages, `has_diagram` / `has_table`, relevance. |
| **`get_page_image`** | Checks which **page PNGs** exist under `files/pages/{source}/`. Does **not** return pixels — the client loads images via **`GET /page/...`**. Use when a manual diagram or photo should appear; then emit **`manual_image`** blocks using `pages_found`. |
| **`find_relevant_pages`** | Lists which manual pages best match a **topic** (optional filter for pages that have diagrams). Helps decide where to look before fetching images. |
| **`emit_component`** | Schedules an **interactive React** widget: **`DutyCycleCalculator`**, **`WireSettingsConfigurator`**, or **`PolarityDiagram`**, with props derived from context (duty cycle, wire/material setup, polarity/cables). |

The model may interleave these across iterations (e.g. search → get_page_image → search again → final JSON).

### Chat sessions and compression (`backend/sessions.py`)

- **`POST /chat`** accepts optional **`session_id`**. If omitted, the API creates one and returns it; the client should send it back on the next turns.
- The server stores the **full conversation** the agent needs for the Anthropic API: user text, assistant text, and **tool_use / tool_result** pairs in a JSON-serializable form (`backend/agent.py`).
- When stored messages exceed **24**, older turns are **compressed**: a **Haiku** model (`claude-3-haiku-20240307`) merges that prefix into a rolling **`memory`** string; only the **last 8** messages are kept verbatim. On failure, a **fallback** appends a truncated transcript to `memory`.
- That summary is injected into the **system** prompt under “Earlier in this session” so long chats stay within context limits while preserving important facts (processes, amps/volts, pages, unresolved issues).

Sessions are **in-memory** (lost on API restart) — fine for demos; production would swap in Redis or a DB.

---

## Prerequisites

- **Python 3.10+**
- **Node.js** (18+ recommended)
- **Anthropic API key**

Ingestion rasterizes PDFs with **PyMuPDF** (`pymupdf` in `requirements.txt`).

---

## Environment

With the API started from the **`backend`** directory, copy **`backend/.env.example`** to **`backend/.env`** and set your key:

```bash
cp backend/.env.example backend/.env
```

```env
ANTHROPIC_API_KEY=sk-ant-...
```

`backend/.env` is **gitignored**; do not commit secrets.

---

## Setup and run

### 1. Build the knowledge base (first time / after PDF changes)

From **`backend`** (PDF paths must match `DOCUMENTS` in `ingest.py`):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python ingest.py
```

This writes page images under `files/pages/` and Chroma data under `knowledge_base/`.

### 2. API server

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**. The UI posts to **http://localhost:8000** — keep both processes running.

**Production:** set explicit CORS origins in `main.py` if needed (wildcard subdomains are not always valid in Starlette’s `allow_origins`).

---

## Example prompts (what to expect)

Try these in the chat UI **one at a time**. Wording and exact page numbers can differ by run, but you should see roughly the **block types** below.

### 1. Manual page image (`manual_image`)

**Ask:** *Show me the TIG torch and cable setup diagram from the owner manual. Search the manual, confirm the page exists, and display the actual manual page image in your answer.*

**Expect:** A leading **text** explanation, then a **`manual_image`** block (source + page list); the UI loads PNGs via **`GET /page/{source}/{page}`**. The agent typically uses **`search_knowledge_base`** then **`get_page_image`**.

### 2. Mermaid flowchart (`mermaid`)

**Ask:** *I’m getting porosity in MIG. Give me a Mermaid flowchart (`flowchart TD`) starting from a bad bead, branching through gas, stick-out, base metal cleanliness, and polarity.*

**Expect:** **text** first, then a **`mermaid`** block with a `diagram` string the client renders as a flowchart.

### 3. Inline SVG (`svg`)

**Ask:** *Explain butt vs fillet joints for this welder and include a minimal labeled SVG comparing the two (one `<svg>` with short labels).*

**Expect:** **text** plus an **`svg`** block with `markup` (`<svg>...</svg>`). If you only get text, ask again and insist on an inline SVG after the explanation.

### 4. Interactive component (`component`)

**Ask:** *What’s the duty cycle for MIG welding at 200A on 240V on the OmniPro 220? Use the calculator if it helps.*

**Expect:** **text** grounded in the manual, then a **`component`** block (usually **`DutyCycleCalculator`**) with props such as process, amps, and voltage.

---

## API sketch

**`POST /chat`**

```json
{ "message": "What's the duty cycle for MIG at 200A on 240V?", "session_id": null }
```

Response:

```json
{
  "session_id": "uuid-return-this-on-next-turn",
  "blocks": [ { "type": "text", "content": "..." }, ... ]
}
```

Omit `session_id` on the first message; send the returned `session_id` on follow-ups so the server keeps (and optionally compresses) history.

**`GET /page/{source}/{page_num}`** — JSON with base64 PNG for manual pages used by `manual_image` blocks.

---

## Repo map

| Path | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app, CORS, chat + pages |
| `backend/agent.py` | System prompt, tool loop, block-shaped final JSON |
| `backend/tools.py` | RAG search, page tools, component tool |
| `backend/sessions.py` | Session store + summarization |
| `backend/ingest.py` | PDF → images → chunking → Chroma |
| `frontend/src/components/` | Chat UI, block rendering, interactive widgets |

---

## Design notes (for reviewers)

- **RAG-first:** Search-before-answer policy (see **How the agent works**) — important for equipment safety and trust.
- **Structured blocks:** Typed JSON `blocks` instead of opaque markdown — predictable UI and extension.
- **Vision ingestion:** Page-level chunking plus diagram/table text improves recall for informal “what does it look like” questions.

---

