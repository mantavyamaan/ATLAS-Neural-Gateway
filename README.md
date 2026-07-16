# ATLAS Neural Gateway

## 📖 Overview

ATLAS Neural Gateway is a **pure‑Python routing engine** that selects the best large‑language‑model (LLM) for any user request **without ever calling another LLM** during the decision.  It works by:

1. **Parsing the prompt** once with a tiny ONNX semantic parser to extract its features (task family, complexity, risk tier, required workflow stages).
2. **Fetching live model metadata** from the OpenRouter API (pricing, context window, safety tags, etc.) and turning each model into a rich dictionary stored in a local SQLite registry.
3. **Scoring each candidate** with a set of deterministic utility dimensions (quality, cost, latency, reliability, risk‑fit, runtime‑health, etc.).
4. **Running a 1 500‑iteration Thompson‑Sampling Monte‑Carlo simulation** (fully vectorised with NumPy) to estimate a win‑probability for every model.
5. **Choosing the model with the highest win‑probability** as the primary route, while also providing a confidence score and fallback options.

All of this happens in **sub‑second latency** even with a registry of **~450 models**.

---

## 🏗️ Architecture Diagram (text version)
```
[User Prompt] ──► [ONNX Semantic Parser] ──► TaskFeatures
      │                                         │
      ▼                                         ▼
[OpenRouter Sync] ──► Model Registry (SQLite) ──► Scoring Engine
                                                          │
                                                          ▼
                                                    Thompson Sampling
                                                          │
                                                          ▼
                                                   [Routing Decision]
```

---

## 📦 Core Components

| Component | File | Responsibility |
|-----------|------|----------------|
| **Semantic Parser** | `app/core/semantic_parser.py` | Detects task family, risk tier, complexity, required stages using keyword‑based heuristics. |
| **OpenRouter Sync** | `app/core/openrouter_sync.py` | Pulls live model data from OpenRouter, builds a unified registry entry, **removes any reliance on `real_benchmarks.json`**. |
| **Database Layer** | `app/core/database.py` | Simple SQLite wrapper with thread‑local connections; stores the model registry. |
| **Scoring** | `app/core/scoring.py` | Calculates static scores (cost, latency, reliability, risk‑fit, runtime health) and attaches contextual quality. |
| **Pareto Frontier** | `app/core/scoring.py` | Reduces the candidate set to the non‑dominated elite models. Optimised to extend the frontier instead of replacing it. |
| **Thompson Sampling** | `app/core/scoring.py` | Vectorised Monte‑Carlo simulation (1500 draws). Uses a deterministic seed based on model names + task family. |
| **Planning** | `app/core/planning.py` | Builds single‑model or multi‑stage execution plans and applies cost/latency estimations. |
| **Router** | `app/core/router.py` | Orchestrates the whole pipeline, applies the confidence threshold, and returns the final `RoutingDecision`. |
| **Embedding Parser (ONNX)** | `app/core/embedding_parser.py` | Light‑weight embedding model used only for the semantic parser. |

---

## 🔄 Dynamic Benchmark Sync (no `real_benchmarks.json`)

* The previous version shipped a static `real_benchmarks.json` file and fell back to it when the OpenRouter API lacked performance numbers.
* **Now:** `openrouter_sync.py` **does not read any file**. All scoring data is derived from live OpenRouter metadata (`pricing`, `context_length`, `capabilities`, etc.) and from **on‑the‑fly** calculations such as:
  * **Relative cost score** – normalises input/output cost to a per‑million‑token basis.
  * **Utility dimensions** – cost, latency, reliability, risk‑fit, runtime health.
* The `evidence` block is always set to `{"eligible_for_auto_route": false}` because we no longer have curated benchmark evidence.

---

## ⚡ Performance Optimisations (what changed?)

| Issue | Old Behaviour | New Optimised Behaviour |
|-------|----------------|------------------------|
| **Deep copies** | `deepcopy()` was used on every model during scoring and Thompson sampling – ~400 KB per model × 447 models = heavy memory churn. | Replaced with shallow copies (`model.copy()`) or pure read‑only access. |
| **Pareto frontier O(N²)** | Re‑computed vectors for each comparison inside nested loops. | Pre‑computed the Pareto vectors once, then compared simple tuples. Also **extends** the frontier instead of discarding it when the set is too small. |
| **Thompson sampling loops** | Python `for` loops over 1500 simulations, calling `bounded_beta_sample` per model – several seconds. | Fully vectorised using NumPy: generate a `(1500, N_models)` beta matrix in one call, compute utilities with broadcasting, and count wins via `np.argmax`. Latency dropped from ~2 s to **≈0.05 s** on a 447‑model registry. |
| **Deterministic seeding** | Random seed was recomputed each run but not guaranteed to be reproducible across processes. | Seed now hashes the sorted list of model names + task family, guaranteeing identical Monte‑Carlo results for identical inputs. |
| **Confidence threshold** | Fixed at 0.4, but could be overridden incorrectly. | Still 0.4 by default, but the routing code now logs the confidence and automatically escalates/abstains when `top_confidence < 0.4`. |

---

## 🧭 How Routing Works – Step‑by‑Step (simple words)

1. **User sends a prompt** to the FastAPI server (`/route`).
2. **Parser runs once** – extracts which *family* (chat, coding, etc.), how *complex* it is, and whether it needs *multiple stages*.
3. **Registry is queried** – all models are loaded from the SQLite DB.
4. **Eligibility filter** – models that don’t support the required family, exceed the user’s latency/cost limits, or are marked unsafe are discarded.
5. **Contextual quality is attached** – each model receives a `q` dict with a runtime‑adjusted mean quality, uncertainty, and other stats.
6. **Pareto frontier** – from the eligible set, the engine keeps only the *non‑dominated* models (those that are not strictly worse on every utility dimension).
7. **Utility scoring** – each frontier model gets a single deterministic utility value based on the selected weighting profile (`balanced`, `quality_first`, `budget_first`, etc.).
8. **Thompson Sampling** – 1 500 simulations are run **in parallel** using NumPy. For each simulation the model’s quality is jittered according to its uncertainty, the utility is recomputed, and the model with the highest utility gets a “win”.
9. **Win probabilities** – after the simulations, each model’s win count is divided by 1 500. The model with the highest win probability becomes the *primary* candidate; the second‑best becomes a *fallback*.
10. **Confidence** – the primary model’s win probability is stored as the router’s confidence score. If the confidence < 0.4, the router either **abstains** or **escalates** to a human operator (configurable).
11. **Response** – the server returns a JSON payload containing the selected model name, confidence, fallback list, and the full planning details (cost estimate, latency estimate, etc.).

---

## 🛠️ Running the Service

```bash
# 1️⃣ Install dependencies (Python 3.12)
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# 2️⃣ Initialise the SQLite registry (creates atlas_registry.db)
python -c "from app.core.database import init_db; init_db()"

# 3️⃣ Pull the latest OpenRouter model list and sync it to the DB
python scripts/run_benchmark_sync.py   # (or) python -c "from app.core.openrouter_sync import sync_openrouter_models; sync_openrouter_models()"

# 4️⃣ Start the FastAPI server (Uvicorn)
uvicorn app.main:app --host 0.0.0.0 --port 8080
```

The server will now be reachable at `http://127.0.0.1:8080/route`. Send a POST request with JSON `{"prompt": "…"}` and you’ll receive the routing decision.

---

## 📊 Monitoring & Debugging

* **Latency** – The `estimate_confidence` function prints the time for each request (≈0.05 s with 447 models). 
* **Win‑probability** – Look at `decision.confidence` in the JSON response to see how sure the router is. 
* **Database** – Inspect `atlas_registry.db` with any SQLite viewer to see the raw model entries.
* **Logging** – All major steps use the standard `logging` module; adjust `logging.basicConfig(level=logging.DEBUG)` for more verbosity.

---

## 🤝 Contributing

1. Fork the repository.
2. Create a feature branch (`git checkout -b my‑feature`).
3. Ensure the test suite passes (`pytest -q`).
4. Submit a Pull Request with a clear description of the change.

Please keep the **no‑LLM‑in‑the‑middle** rule: any routing‑related logic must be pure mathematics or deterministic heuristics.

---

## 📜 License

This project is released under the **MIT License** – you are free to use, modify, and redistribute it.

---

**Happy routing!** If you run into any issues, feel free to open an issue on GitHub or contact the maintainers.
