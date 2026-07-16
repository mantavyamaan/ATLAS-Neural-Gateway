# 🌌 ATLAS Neural Gateway: How It Works (End-to-End)

The ATLAS Neural Gateway is an **Enterprise-grade AI Routing Gateway**. Its primary job is to act as an intelligent middleman between you (the user) and a vast array of AI models (like GPT-4, Claude 3.5 Sonnet, Gemini 1.5 Pro, Llama 3, etc.).

When you write a prompt, it doesn't just blindly send it to the most expensive model. Instead, it uses **Bayesian Inference** and **Thompson Sampling** to mathematically prove which model will give you the best result for the lowest cost and fastest latency.

Here is exactly what happens under the hood from the moment you click "Route Request" to the moment you get a response.

---

## 🛑 Stage 1: The Vector Embedding Parsing Engine
The moment you click **"Route Request"**, your prompt and any uploaded files are intercepted by a **Pure Vector Embedding Engine** (`BAAI/bge-large-en-v1.5`) running locally inside the FastAPI backend. Unlike traditional routers that rely on slow LLM generation or rigid regex keywords, this parser uses pure mathematics to achieve sub-millisecond categorization.

### The Logistic Regression & Cross-Encoder Architecture
1. **Mathematical Coordinate Mapping:** The BAAI embedding model instantly converts your natural language prompt into a massive 1024-dimensional mathematical coordinate vector.
2. **Logistic Regression Classifiers:** The gateway passes this vector through three distinct, highly-trained Logistic Regression models to strictly predict the task family, domain, and risk tier, eliminating hallucination boundaries.
3. **Cross-Encoder Reranking:** If the Logistic Regression is unsure (i.e., a narrow probability margin between the top two predicted classes), the Engine automatically triggers a secondary local Cross-Encoder (`BAAI/bge-reranker-base`) as a strict tie-breaker.
4. **CI-Gated Adaptation:** You can hit **Train the Engine** in the UI when the gateway misclassifies a prompt. The `/train_parser` API endpoint encodes your corrected prompt, but before saving it, it runs a strict **Golden Evaluation Suite** in a sandbox. If the new vector degrades the matrix below 90% accuracy, the gateway instantly reverts the RAM matrix, ensuring the model can never be poisoned.

### Deterministic Safety Override
While statistical embeddings are brilliant for general intent parsing, they are not trusted with absolute safety. The engine includes a **Monotonic Safety Net**:
1. **Regex Escalation:** If the prompt contains known high-risk terminology (like *"drop table"*, *"suicide"*, *"chest pain"*, or *"lawsuit"*), the parser immediately and deterministically escalates the `risk_tier` to **High** or **Extreme**, regardless of what the statistical neighbors voted.
2. **Statistical Escalation:** Furthermore, if even *one* of the mathematical nearest neighbors belongs to a high-risk tier and the prompt exhibits high ambiguity (entropy), the safety layer proactively raises the risk tier.

This guarantees that dangerous or regulated advice requests are securely handled and flagged before they ever reach an LLM.

---

## 🚪 Stage 2: Hard Feasibility Filtering
With the parsed "Task Summary" in hand, the Gateway consults its local SQLite database (synced live from OpenRouter).

It instantly eliminates any models that mathematically cannot complete your task:
* **Context Window Limit:** If your prompt + files equal 350,000 tokens, it immediately drops any model with a 128K context window (like GPT-4o) and only keeps Long-Context models (like Gemini 1.5 Pro).
* **Cost & Latency SLAs:** If you set your maximum cost slider to $10.00 per million tokens, it drops expensive models (like Claude 3 Opus) that violate your budget.
* **Capabilities:** If you uploaded an image, it drops text-only models (like standard Llama 3) and only keeps Vision models.

*(Note: If no models survive this filter—for example, if you uploaded a 5000-page document but set your budget to $0.10—the Gateway will **Abstain** and refuse to route the request, showing you exactly which constraint was violated).*

---

## 🎲 Stage 3: Bayesian Scoring & Thompson Sampling
Now the Gateway has a list of "Feasible Candidates". It's time to find the absolute best one.

1. **Utility Profiles:** The gateway picks a scoring profile (e.g., `generic_balanced`, `coding_expert`, or `budget_first`) based on your prompt's complexity. 
2. **The 7-Dimension Utility Formula:** Each model is scored on 7 dimensions:
   * **Quality** (How smart is the model?)
   * **Uncertainty** (Is the model inconsistent or unproven?)
   * **Cost** (Input/Output price)
   * **Latency** (How fast does it generate tokens?)
   * **Reliability** (Uptime percentage)
   * **Risk Fit** (Does it hallucinate on medical/legal queries?)
   * **Runtime Health** (Is the provider currently experiencing an outage?)
3. **Thompson Sampling & Task-Conditional Priors:** Instead of just picking the highest static score, the gateway runs a probabilistic simulation (using a Beta Distribution) to balance **Exploration vs. Exploitation**. Crucially, the engine uses **Task-Conditional Priors**—if a model succeeds at "coding", its `alpha` score for coding goes up, but its "OCR" score remains unchanged. This prevents domain bleed.

---

## 🛡️ Stage 4: Tenant Policy Enforcement
Before finalizing the winner, the gateway checks the `TenantContext` (your specific organizational rules).

If your organization has a policy that says *"Never use OpenAI models for Financial Data"* or *"Always prioritize Open-Weight models"*, the Gateway applies those penalties or bans to the Pareto Frontier (the top 3 models).

---

## 🗺️ Stage 5: FrugalGPT Cascades & Plan Generation
The Gateway now has the #1 winning model. It decides if your prompt needs a **Single-Shot Execution** or a **Frugal Cascade**.

* **Standard Tasks:** Generates a standard plan using the winning flagship model and designates 2 "Fallback Models" just in case the primary API goes down.
* **Low-Complexity / Low-Risk Tasks:** The router intentionally intercepts the decision and **cascades to the cheapest, fastest model available** (e.g., `gemini-1.5-flash`). It configures a strict non-LLM Verification Strategy (like Python `ast` or `json.schema`).

---

## 🚀 Stage 6: The Data Plane Proxy (/execute)
The routing plan is generated! Instead of stopping there, the Gateway natively handles the execution and verification loop via the new `POST /execute` proxy endpoint.

1. The API intercepts the plan and your provided `x-openrouter-key`.
2. For Frugal Cascades, it hits OpenRouter using the ultra-cheap model.
3. It seamlessly extracts the markdown artifact block from the response and pumps it through our **Deterministic Verifiers** (running pure Python `ast` or JSON validation in the backend—zero LLM calls required).
4. If the cheap model passes verification, the Gateway returns the response to you, saving you ~90% on API costs.
5. If the cheap model hallucinates or outputs broken syntax, the Gateway automatically falls back, pings OpenRouter again with the expensive flagship model (like `claude-3-5-sonnet`), and returns the perfect response!
