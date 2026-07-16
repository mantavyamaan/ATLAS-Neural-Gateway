import json
import sys
import os

# Add parent dir to sys.path to allow importing app
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app.core.embedding_parser import get_parser
from app.core.router import route
from app.core.database import init_db

def run_eval():
    init_db()
    eval_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "golden_eval.json")
    with open(eval_file, "r", encoding="utf-8") as f:
        prompts = json.load(f)

    parser = get_parser()

    parser_matches = 0
    routing_matches = 0
    routing_evaluated = 0
    
    abstain_correct = 0
    total_abstained = 0

    for prompt_data in prompts:
        text = prompt_data["text"]
        expected_family = prompt_data["primary_family"]
        expected_domain = prompt_data["domain"]
        expected_risk = prompt_data["risk_tier"]
        acceptable_models = prompt_data["acceptable_models"]

        # Run Parser
        parsed = parser.parse(text)
        
        if (parsed.primary_family == expected_family and
            parsed.domain == expected_domain and
            parsed.risk_tier == expected_risk):
            parser_matches += 1

        # Run Router
        decision = route(prompt=text)
        
        abstained_or_escalated = decision.abstain or decision.escalate_to_human
        
        if abstained_or_escalated:
            total_abstained += 1
            # Check if high-risk or ambiguous
            is_high_risk = expected_risk in ["high", "extreme"]
            is_ambiguous = parsed.ambiguity_score > 0.6
            if is_high_risk or is_ambiguous:
                abstain_correct += 1
        else:
            if decision.selected_plan and decision.selected_plan.selected_model:
                routing_evaluated += 1
                if decision.selected_plan.selected_model in acceptable_models:
                    routing_matches += 1
                    
    parser_accuracy = parser_matches / len(prompts) if prompts else 0
    routing_accuracy = routing_matches / routing_evaluated if routing_evaluated > 0 else 0
    abstain_precision = abstain_correct / total_abstained if total_abstained > 0 else 1.0
    
    print(f"Parser Accuracy: {parser_accuracy * 100:.2f}%")
    print(f"Routing Accuracy: {routing_accuracy * 100:.2f}%")
    print(f"Abstain Precision: {abstain_precision * 100:.2f}%")

    if parser_accuracy >= 0.90:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    run_eval()
