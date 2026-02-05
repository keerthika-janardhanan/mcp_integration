# From Recorder to Automation Script: Step-by-Step

This guide explains, in simple English, how the system turns a recorded flow into automation scripts, including which files and methods are involved.

## Big Picture
- You record a flow (Playwright Python recorder) → artifacts are ingested → refined steps are stored in the vector DB (Chroma).
- The Agent gathers context (vector steps, existing repo snippets) and produces:
  - A human-friendly preview of steps (optionally LLM‑assisted).
  - A deterministic script payload (locators/pages/tests) aligned to your framework.
- Today, code files are generated deterministically (no LLM); the LLM is used for the preview/refinement and has a disabled code‑gen path you can enable later.

---

## 1) Record and Ingest
- Recorder (Python): `app/run_playwright_recorder_v2.py`
  - Writes a session under `recordings/<session>/` with DOM, screenshots, `network.har`, `trace.zip`, and `metadata.json`.
- Ingestion to Vector DB:
  - Main helpers: `app/ingest.py`, `app/ingest_utils.py`, `app/vector_db.py`
  - Vector client: `app/vector_db.py::VectorDBClient`
    - `add_document(source, doc_id, content, metadata)` stores refined recorder “step” documents as `type: "recorder_refined"`, with `record_kind: "step"`, `step_index`, `action`, `navigation`, `data`, `expected`, `flow_slug`, `flow_name`, plus `payload.locators/element`.

What gets stored (important fields for generation):
- `metadata.type = "recorder_refined"`
- `metadata.record_kind = "step"` (only step records are used to build flows)
- `metadata.step_index`, `action`, `navigation`, `data`, `expected`, `flow_slug`, `flow_name`
- `payload.locators` (e.g., Playwright `getByRole` hints, CSS/XPath) and `payload.element` (fallback tag/role/name)

---

## 2) Vector DB Lookups (Fetching Refined Steps)
- File: `app/agentic_script_agent.py`
- Methods:
  - `_collect_vector_flow_steps(scenario: str, top_k: int = 256)`
    - Queries the vector DB for `type: "recorder_refined"` docs matching your scenario’s flow.
    - Uses `VectorDBClient.query_where(...)` and `list_where(...)` under the hood.
  - `_steps_from_vector_docs(docs, default_flow_slug)`
    - Builds an ordered list of steps from the vector documents using `step_index`.

- Vector DB client: `app/vector_db.py::VectorDBClient`
  - `query_where(query, where, top_k=3)`
  - `list_where(where, limit=1000)` (delegates to `get_where`) 
  - `query(query, top_k=3)`

Notes:
- Only `record_kind:"step"` entries are assembled; `record_kind:"element"` is ignored for the flow but can help selector self‑healing later.

---

## 3) Build the Preview (Human Steps)
- File: `app/agentic_script_agent.py`
- Methods:
  - `gather_context(scenario)`
    - Pulls vector refined steps, existing script excerpts, and scaffold snippets from the repo (via vector DB + filesystem).
  - `generate_preview(scenario, framework, context)`
    - Formats steps for preview using `_format_steps_for_prompt(steps)`.
    - Optional LLM preview: if `USE_LLM_PREVIEW=true`, the preview text is refined via Azure OpenAI.
  - `refine_preview(scenario, framework, previous_preview, feedback, context)`
    - Lets the LLM adjust the preview based on user feedback.

LLM prompts used (for preview only):
- `self.preview_prompt` and `self.refine_prompt` (initialized in `AgenticScriptAgent.__init__`).

Important: `_format_steps_for_prompt` only formats already‑fetched steps. It does not fetch from the vector DB.

---

## 4) Generate Code Files (Deterministic Path)
- File: `app/agentic_script_agent.py`
- Methods:
  - `generate_script_payload(scenario, framework, accepted_preview)`
    - Filters/aligns vector steps to the accepted preview (signatures/phrases).
    - Calls `_build_deterministic_payload`.
  - `_build_deterministic_payload(scenario, framework, vector_steps, keep_signatures)`
    - Produces three artifacts in memory:
      - `locators/<slug>.ts` (a `locators` object)
      - `pages/<CamelCaseSlug>Page.ts` (Page Object with methods wired to data keys)
      - `tests/<slug>.spec.ts` (Playwright test spec using the Page Object)
    - Selector strategy: prefers Playwright `getByRole/getByLabel/getByText` from refined steps; falls back to CSS/XPath when needed.
    - Data strategy: builds typed methods like `setSupplier`, `setNumber`, `setAmount`, and wires `applyData(...)` to Excel columns.

Where framework structure comes from:
- `FrameworkProfile.from_root(...)` detects `locators/pages/tests` directories in the target repo.
- `_fetch_scaffold_snippet(...)` pulls small code snippets from the repo (via vector DB with `type:"script_scaffold"`) to guide structure.

---

## 5) LLM Code Generation (Available but Not the Default)
- File: `app/llm_client.py`
  - `ask_llm_for_script(structure, existing_script, test_case, enriched_steps, ui_crawl, framework_prompt)`
    - Builds a comprehensive prompt and calls Azure OpenAI to return code.
- File: `app/orchestrator.py`
  - Shows a commented example of calling `ask_llm_for_script(...)` and then trial‑running and self‑healing.
- File: `app/agentic_script_agent.py`
  - Defines `self.script_prompt` but does not currently invoke it.

Summary: Today, the agent generates files without the LLM for code. Only the preview/refine steps use the LLM by default. You can wire the LLM code‑gen path back if desired.

---

## 6) Frontend + API Flow (Where Buttons Call What)
- Frontend API: `frontend/src/api/agentic.ts`
  - `previewAgentic(scenario)` → POST `/agentic/preview` → calls `AgenticScriptAgent.generate_preview(...)`.
  - `generatePayload(scenario, acceptedPreview)` → POST `/agentic/payload` → calls `AgenticScriptAgent.generate_script_payload(...)` and returns `{ locators, pages, tests }`.
  - `persistFiles(files, token, frameworkRoot?)` → POST `/agentic/persist` → writes files to detected repo structure.
  - `trialRun...` endpoints call backend to run a temporary spec and report logs.

- Backend endpoints: `app/api/routers/agentic.py` (not shown here)
  - Implements `/agentic/preview`, `/agentic/payload`, `/agentic/persist`, `/agentic/trial-run*`.

---

## 7) Retrieval Details and Limits
- Vector queries use caps, not “fetch all”:
  - Steps: `_collect_vector_flow_steps(..., top_k=256)`
  - Scaffolds: `_fetch_scaffold_snippet(..., limit=3, max_chars=1500)`
  - Existing assets: `find_existing_framework_assets(..., top_k=8)`
- Vector client defaults: `query/query_where` default to `top_k=3` unless overridden; `list_where`/`get_where` default `limit=1000`.
- Preview truncation (optional): `PREVIEW_MAX_STEPS` environment variable.

---

## 8) Self‑Healing (When Things Break)
- File: `app/llm_client.py`
  - `ask_llm_to_self_heal(failed_script, logs, ui_crawl)`
    - If trial run shows locator failures, LLM proposes corrected selectors using UI crawl data. Updates the locator cache.
- Locator cache: `./locator_cache.json` via `load_locator_cache/save_locator_cache`.

---

## TL;DR: Key Methods by Stage
- Fetch refined steps: `AgenticScriptAgent._collect_vector_flow_steps` → `VectorDBClient.query_where/list_where`
- Format steps for preview: `AgenticScriptAgent._format_steps_for_prompt`
- Preview (LLM optional): `AgenticScriptAgent.generate_preview` / `refine_preview`
- Build code (deterministic): `AgenticScriptAgent.generate_script_payload` → `_build_deterministic_payload`
- LLM code‑gen (optional path): `llm_client.ask_llm_for_script` (not wired by default)

If you want, I can wire the `script_prompt` or `llm_client.ask_llm_for_script` into the `/agentic/payload` path to let GPT generate TypeScript directly instead of using the deterministic generator.
