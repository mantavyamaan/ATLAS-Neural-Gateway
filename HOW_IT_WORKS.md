# 🌌 ATLAS Neural Gateway: How It Works (End-to-End)

The ATLAS Neural Gateway is an **Enterprise-grade AI Routing Gateway**. Its primary job is to act as an intelligent middleman between you (the user) and a vast array of AI models (like GPT-4, Claude 3.5 Sonnet, Gemini 1.5 Pro, Llama 3, etc.).

When you write a prompt, it doesn't just blindly send it to the most expensive model. Instead, it uses **Bayesian Inference** and **Thompson Sampling** to mathematically prove which model will give you the best result for the lowest cost and fastest latency.

Here is exactly what happens under the hood from the moment you click "Route Request" to the moment you get a response.

---

## 🛑 Stage 1: The Vector Embedding Parsing Engine
The moment you click **"Route Request"**, your prompt and any uploaded files are intercepted by a **Pure Vector Embedding Engine** (`BAAI/bge-large-en-v1.5`) running locally inside the FastAPI backend. Unlike traditional routers that rely on slow LLM generation or rigid regex keywords, this parser uses pure mathematics to achieve sub-millisecond categorization.

### The K-Nearest Neighbors (KNN) Architecture
1. **Mathematical Coordinate Mapping:** The BAAI embedding model instantly converts your natural language prompt into a massive 1024-dimensional mathematical coordinate vector.
2. **The Memory Bank:** The gateway maintains a highly diverse, flat JSON dataset (`semantic_examples.json`) of nearly 3,000 real-world examples, all pre-calculated into a lightning-fast `.npy` coordinate matrix in memory.
3. **Softmax Voting:** The engine finds the mathematical nearest neighbors (the closest coordinates in the dataset) to your prompt. It then applies a temperature-weighted Softmax formula, allowing the neighbors to "vote" independently on what task family, domain, and risk tier your prompt belongs to.
4. **Instant Adaptation:** Because this relies entirely on the dataset coordinate space, the gateway learns your exact workflow and edge cases on the fly. You can hit **Train the Engine** in the UI when the gateway misclassifies a prompt. The `/train_parser` API endpoint encodes your corrected prompt, mathematically hot-swaps the new vector directly into RAM, and permanently saves it to the JSON file. It instantly becomes precise on the very next request—bypassing the need to restart the server or retrain neural networks!

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
3. **Thompson Sampling:** Instead of just picking the highest static score, the gateway runs a probabilistic simulation (using a Beta Distribution) to balance **Exploration vs. Exploitation**. It mathematically calculates the **Win Probability** (the exact % chance that a model will outperform all others for this specific task).

---

## 🛡️ Stage 4: Tenant Policy Enforcement
Before finalizing the winner, the gateway checks the `TenantContext` (your specific organizational rules).

If your organization has a policy that says *"Never use OpenAI models for Financial Data"* or *"Always prioritize Open-Weight models"*, the Gateway applies those penalties or bans to the Pareto Frontier (the top 3 models).

---

## 🗺️ Stage 5: Plan Generation (Single vs. Multi-Stage)
The Gateway now has the #1 winning model. It decides if your prompt needs a **Single-Model Plan** or a **Multi-Stage Plan**.

* **Simple Tasks:** Uses a Single-Model Plan and designates 2 "Fallback Models" just in case the primary API goes down.
* **Complex/Extreme Tasks:** If your prompt is highly ambiguous or asks for verifiable facts, it creates a Multi-Stage Plan. It might pick `claude-3.5-sonnet` to generate the code, but assign `gpt-4o-mini` as a **Verifier** to double-check the code before returning it to you.

---

## 🚀 Stage 6: The Frontend Handoff & Generation
The routing is complete! The FastAPI backend sends the final `decision_record` back to the Streamlit UI in under **150 milliseconds**.

1. The UI renders the beautiful green **"Routing successful!"** banner.
2. It displays the **Selected Model**, Estimated Latency, Estimated Cost, and the Gateway's Confidence Level.
3. You review the choice.
4. When you click **"Generate Response with Selected Model"**, the UI takes the winning model ID and your OpenRouter API Key, connects directly to the OpenRouter generation endpoint, and streams the AI's response directly onto your screen!
