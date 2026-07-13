# ATLAS Neural Gateway

**Adaptive Task and LLM Allocation System** — a complete, end-to-end AI agent and neural routing gateway, exposed as a FastAPI service. ATLAS decides *which model or execution plan* should handle a request, taking into account task requirements, governance policy, runtime health, cost, latency, uncertainty, and SLAs. It then acts as an intelligent proxy to actively generate and stream the final response directly back to the user.

## How it's organized

```
atlas_neural_gateway/
├── app/
│   ├── main.py                 # FastAPI app entrypoint (uvicorn target)
│   ├── config.py                # version stamps + confidence thresholds
│   ├── models/
│   │   ├── schemas.py            # internal dataclasses (TaskFeatures, ExecutionPlan, ...)
│   │   ├── catalog.py             # provider -> model name catalog
│   │   ├── registry_builder.py     # fallback heuristics for unmapped models
│   │   └── real_benchmarks.json    # ground-truth benchmark overrides
│   ├── core/
│   │   ├── database.py              # SQLite database and persistence layer
│   │   ├── openrouter_sync.py       # fetches live models and pricing from OpenRouter API
│   │   ├── artifact_inspection.py   # PDF/image/audio/video/xlsx/pptx inspection
│   │   ├── semantic_parser.py        # deterministic + heuristic task parsing
│   │   ├── feasibility.py             # hard constraint filtering
│   │   ├── policy.py                   # governance / policy engine
│   │   ├── scoring.py                   # Bayesian quality, Pareto, utility, confidence
│   │   ├── planning.py                   # single-model & multi-stage plan generation
│   │   ├── router.py                      # route() — the main pipeline
│   │   └── formatting.py                   # human-readable decision summaries
│   └── api/
│       ├── schemas.py                       # pydantic request/response models
│       └── routes.py                         # FastAPI endpoints
├── tests/
│   └── test_router.py                         # end-to-end scenario tests
├── requirements.txt
├── .env.example
└── README.md
```

This mirrors the routing pipeline described in the ATLAS design doc:

```
Request -> Artifact Inspection -> Semantic Parsing -> Task Representation
   -> Feasibility Filtering -> Policy Enforcement -> Bayesian Quality
   -> Pareto Reduction -> Utility Scoring -> Confidence Estimation
   -> Execution Plan -> Route / Escalate / Abstain
```

## Setup (VS Code / local)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Optional artifact-inspection libraries (`pymupdf`, `Pillow`, `openpyxl`,
`python-pptx`, `mutagen`) are in `requirements.txt` but the router degrades
gracefully if any are missing — it just falls back to prompt-keyword
heuristics for that modality. `ffprobe` (from ffmpeg) is used for
audio/video duration if present on the host `PATH`.

## Prerequisites (Ollama & Local LLM Parser)

ATLAS uses a high-precision Bayesian classifier powered by **Llama 3.1** to semantically parse and categorize prompts before they are routed. 
This requires a local installation of Ollama.

1. **Install Ollama** from [ollama.com](https://ollama.com).
2. **Download Llama 3.1** by running this in your terminal:
   ```bash
   ollama run llama3.1
   ```
   *(If your Ollama server is offline, ATLAS will gracefully fall back to its internal heuristic/regex parser).*

## Run the Service & UI

ATLAS now features a premium **Streamlit Frontend** with Glassmorphism design, Custom Model Allowlisting, and Stage 2 LLM execution (directly streaming responses from OpenRouter using the dynamically selected optimal model).

You need two terminals to run the full stack:

**Terminal 1 (Backend API):**
```bash
uvicorn app.main:app --reload --port 8000
```
*(Interactive Swagger docs available at **http://127.0.0.1:8000/docs**)*

**Terminal 2 (Frontend Dashboard):**
```bash
streamlit run frontend.py   // streamlit run frontend.py --server.port 8505   if already have something running in that port
```

## Example request

```bash
curl -X POST http://127.0.0.1:8000/route \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Implement a concurrent web crawler in Python with rate limiting and structured JSON output.",
    "input_formats": ["text"],
    "estimated_tokens": 3000,
    "estimated_output_tokens": 4000,
    "profile_name": "balanced"
  }'
```

Response shape (abridged):

```json
{
  "abstain": false,
  "escalate_to_human": false,
  "selected_plan": {
    "plan_id": "...",
    "plan_type": "single_model",
    "selected_model": "GPT-5.4",
    "fallback_models": ["Claude-Sonnet-4.6", "Gemini-3-Pro"],
    "verifier_models": [],
    "expected_latency_ms": 2150.4,
    "expected_cost_usd": 0.0182,
    "confidence": 0.61
  },
  "decision_record": { "...": "full auditable trace" },
  "summary_text": "=== Atlas Router Decision === ..."
}
```

## Endpoints

| Method | Path             | Purpose |
|--------|------------------|---------|
| POST   | `/route`         | Run the full routing pipeline for a request |
| POST   | `/outcome`       | Feed an observed outcome back into a model's Bayesian priors |
| GET    | `/models`        | List the canonical registry (summary view) |
| GET    | `/models/{name}` | Full registry entry for one model |
| POST   | `/models`        | Dynamically add or update a model in the SQLite registry |
| DELETE | `/models/{name}` | Remove a model from the registry |
| GET    | `/versions`      | Current version stamps for every subsystem |
| GET    | `/health`        | Liveness probe |

## The Model Registry (Dynamic SQLite + OpenRouter)

ATLAS uses a real-time, dynamic **SQLite database** to store its model registry, making it a production-ready routing engine.

When the application starts, `app/core/openrouter_sync.py` connects to the **OpenRouter API** to download the latest available models, their exact context window limits, and live pricing.

To ensure routing decisions are mathematically precise, it cross-references these models against `app/models/real_benchmarks.json`, which contains manually curated, **ground-truth benchmark scores** (like SWE-Bench and MMLU equivalents) for flagship models like GPT-4o, Claude 3.5 Sonnet, and Llama 3. 

For obscure community models that aren't mapped in our benchmark JSON, it explicitly defaults them to an "insufficient evidence" state. By default, `ATLAS_REQUIRE_MEASURED_EVIDENCE=true` prevents these unknown models from receiving auto-routed traffic unless the tenant overrides the behavior. Tests are also run deterministically to ensure the suite is blazingly fast and works entirely offline.

## Plugging in a real semantic parser

By default, task understanding uses `fallback_structured_semantic_parse()`
(keyword heuristics) in `app/core/semantic_parser.py`. To use a real
structured-output LLM parser instead, pass an `llm_parser` callable into
`route()` — it must return a `StructuredSemanticParse` (or an equivalent
dict) and is validated via `validate_structured_parse()`. This isn't wired
into the HTTP layer by default; add it in `app/api/routes.py` where
`route()` is called.

## Testing

```bash
pytest tests/ -v
```

## Production requirements

ATLAS is a routing control plane, not a model executor. A production
deployment must invoke the selected plan in a separate execution service,
verify outputs, and submit authenticated outcomes. Name-derived fallback
scores are development fixtures only: with the default
`ATLAS_REQUIRE_MEASURED_EVIDENCE=true`, models without curated benchmark or
measured production evidence are rejected before scoring. Populate the
registry with versioned capability probes, task-family evaluations, and real
provider telemetry before enabling automatic routing.

Set `ATLAS_ADMIN_API_KEY` before enabling the mutable model and outcome
endpoints. Do not expose server-local `files` paths; use authenticated uploads
or object-store references instead.

Tests mirror the original design-doc demonstration scenarios: a coding
task, a high-risk legal contract review, audio summarization, an
offensive-security policy denial, a budget-constrained support task,
long-context research with citations, and file-driven conflict detection.

## Design principles (from the spec)

1. **Hard constraints override soft preferences** — feasibility filtering
   runs before any scoring.
2. **Policy is independent of scoring** — governance never hides inside
   utility weights.
3. **Runtime conditions matter** — latency, availability, queue pressure,
   and incident status all feed into routing, not just benchmarks.
4. **Uncertainty is quantified** — Thompson Sampling estimates confidence
   rather than returning a bare point estimate.
5. **Derive signals, don't duplicate them** — everything traces back to
   the canonical registry.
6. **Every decision is reproducible** — each `RoutingDecision` carries a
   reproducibility hash plus per-subsystem version stamps.
7. **Multi-stage workflows get structured planning** — OCR, document QA,
   summarization, etc. can be routed to different specialist models within
   one plan.
8. **Mathematical Purity** — Cost/Latency are strictly enforced as absolute filters, ranking uses purely absolute scale utilities (no min-maxing), Bayesian priors never double count observations, and confidence scores explicitly distinguish between Thompson Sampling win-rates and actual predicted task success.
