import json
from typing import List
from openai import OpenAI
import logging

from app.models.schemas import ArtifactProfile, StructuredSemanticParse
from app.core.semantic_parser import fallback_structured_semantic_parse
from app.config import ATLAS_PARSER_API_KEY, ATLAS_PARSER_BASE_URL, ATLAS_PARSER_MODEL_CLOUD
from app.core.database import get_feedback_examples

logger = logging.getLogger(__name__)

# Initialize the OpenAI client dynamically
client = OpenAI(
    base_url=ATLAS_PARSER_BASE_URL,
    api_key=ATLAS_PARSER_API_KEY if ATLAS_PARSER_API_KEY else "ollama",
    max_retries=0,  # Prevent default 2 retries from causing >60s hangs
    timeout=45.0    # Fail fast so it falls back to heuristics before Streamlit times out
)

def call_llm_parser(
    prompt: str,
    input_formats: List[str],
    estimated_tokens: int,
    artifacts: List[ArtifactProfile]
) -> StructuredSemanticParse:
    """
    Calls a local LLM via Ollama to semantically parse the prompt into a StructuredSemanticParse object.
    Falls back to the heuristic parser if Ollama is unavailable or fails to return valid JSON.
    """
    
    system_prompt = """You are the Semantic Parsing Engine for the ATLAS Neural Gateway.
Your job is to analyze the user's prompt and output a STRICT JSON object representing the routing requirements.
You must return ONLY valid JSON. Do not wrap it in markdown block quotes (like ```json), just the raw JSON.

The JSON schema must exactly match this structure:
{
  "primary_family": "string (Options: chat, coding, reasoning, mathematics, vision, ocr, document_qa, audio, agent, translation, summarization, image_generation, video_generation)",
  "secondary_families": ["string"],
  "domain": "string (e.g. medical, legal, finance, security, software, general)",
  "risk_tier": "string (low, medium, high, extreme)",
  "risk_type": "string (standard, regulated_advice, operational, security_sensitive)",
  "expected_output": "string (free_text, code, structured_json, image, video)",
  "ambiguity_score": float (0.0 to 1.0, where 1.0 means highly ambiguous/unclear)",
  "actionability": "string (advisory, high)",
  "document_type": "string (e.g. generic, contract, medical_record, codebase)",
  "decomposition_needed": boolean (true if task requires multiple steps/tools),
  "needs_verification": boolean (true if facts/code must be verified),
  "required_stages": ["string"] (e.g. ["coding", "domain_reasoning"]),
  "reason_summary": "string (Brief 1 sentence explanation of your classification)"
}

Here are some examples of how you should classify requests:
Prompt: "generate an image of me playing soccer"
-> "primary_family": "image_generation", "expected_output": "image"

Prompt: "create a short video of a dog running"
-> "primary_family": "video_generation", "expected_output": "video"

Prompt: "write a python script to scrape a website"
-> "primary_family": "coding", "expected_output": "code"

Prompt: "what is the capital of France?"
-> "primary_family": "chat", "expected_output": "free_text"
"""

    # Fetch and inject dynamic few-shot examples from the Memory Bank
    try:
        feedback_examples = get_feedback_examples(limit=5)
        if feedback_examples:
            system_prompt += "\n\n# Dynamic User Corrections (Prioritize these!)\n"
            for ex in feedback_examples:
                system_prompt += f'Prompt: "{ex["prompt"]}"\n-> "primary_family": "{ex["correct_family"]}"\n\n'
    except Exception as e:
        logger.warning(f"Failed to load dynamic feedback examples: {e}")

    try:
        response = client.chat.completions.create(
            model=ATLAS_PARSER_MODEL_CLOUD,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze this prompt:\n{prompt}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            timeout=30.0 # Increased timeout to allow Ollama to load the model into memory
        )
        
        raw_json = response.choices[0].message.content
        data = json.loads(raw_json)
        
        # Build workflow graph heuristically from the required stages
        stages = data.get("required_stages", [])
        if not stages:
            stages = [data.get("primary_family", "chat")]
            
        workflow_graph = []
        for i, stage in enumerate(stages):
            workflow_graph.append({
                "stage_id": i + 1,
                "stage_name": stage,
                "depends_on": [] if i == 0 else [i],
                "fallbacks_prepared": True,
            })
            
        return StructuredSemanticParse(
            primary_family=data.get("primary_family", "chat"),
            secondary_families=data.get("secondary_families", []),
            required_stages=stages,
            workflow_graph=workflow_graph,
            domain=data.get("domain", "general"),
            risk_tier=data.get("risk_tier", "low"),
            risk_type=data.get("risk_type", "standard"),
            expected_output=data.get("expected_output", "free_text"),
            ambiguity_score=float(data.get("ambiguity_score", 0.15)),
            actionability=data.get("actionability", "advisory"),
            document_type=data.get("document_type", "generic"),
            decomposition_needed=bool(data.get("decomposition_needed", False)),
            needs_verification=bool(data.get("needs_verification", False)),
            parser_confidence=0.95, # High confidence since we used an LLM
            reason_summary=data.get("reason_summary", "Parsed via Llama 3.1 local")
        )
        
    except Exception as e:
        logger.warning(f"LLM Parser failed ({str(e)}). Falling back to heuristic parser.")
        return fallback_structured_semantic_parse(prompt, input_formats, estimated_tokens, artifacts)
