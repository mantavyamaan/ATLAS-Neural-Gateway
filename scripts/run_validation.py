import sys
import os
import time
import random
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))
from app.core.router import route

def run_validation(num_tests=50000):
    print(f"Initializing validation with {num_tests} test cases...")
    print("Pre-warming router (this will rebuild the KNN matrix if the dataset changed)...")
    
    # Pre-warm
    _ = route("hello")
    print("Router pre-warmed.")
    
    # Generate test cases (different from the training templates to test generalization)
    test_cases = []
    
    # HIGH complexity testing
    high_verbs = ["Please provide a detailed architecture for", "I need a complete implementation of", "Can you help me rewrite", "Perform an exhaustive analysis of"]
    high_topics = ["a multi-tenant SaaS application", "a high frequency trading bot", "a globally distributed database", "a custom neural network from scratch", "an autonomous driving perception module"]
    
    for _ in range(int(num_samples * 0.34)):
        test_cases.append({
            "prompt": f"{random.choice(high_verbs)} {random.choice(high_topics)}",
            "expected_profile": "quality_first"
        })
        
    # MEDIUM complexity testing
    medium_verbs = ["How do I fix", "Can you review this code for", "Write a python script for", "Show me how to use"]
    medium_topics = ["Flask file uploads", "pandas dataframe merging", "React useEffect hooks", "PostgreSQL left joins", "Docker port forwarding"]
    
    for _ in range(int(num_samples * 0.33)):
        test_cases.append({
            "prompt": f"{random.choice(medium_verbs)} {random.choice(medium_topics)}",
            "expected_profile": "balanced"
        })
        
    # LOW complexity testing
    low_prompts = ["hey there", "good evening", "hows it going", "tell me something funny", "thanks for the help", "goodbye", "hello world"]
    
    for _ in range(int(num_samples * 0.33)):
        test_cases.append({
            "prompt": f"{random.choice(low_prompts)} {random.randint(1, 1000)}",
            "expected_profile": "budget_first"
        })
        
    random.shuffle(test_cases)
    
    correct = 0
    total = len(test_cases)
    
    print(f"Starting execution of {total} test cases...")
    start_time = time.time()
    
    for i, tc in enumerate(test_cases):
        if i > 0 and i % 5000 == 0:
            elapsed = time.time() - start_time
            print(f"Processed {i}/{total} cases... (Accuracy so far: {(correct/i)*100:.2f}%) [{elapsed:.1f}s]")
            
        decision = route(tc["prompt"])
        profile = decision.selected_plan.profile_used if decision.selected_plan else "None"
        
        # We expect high to go to quality_first (or high_risk), medium to balanced, low to budget_first
        # Allow high_risk for high complexity since complexity=high forces risk=high
        if tc["expected_profile"] == "quality_first" and profile in {"quality_first", "high_risk"}:
            correct += 1
        elif tc["expected_profile"] == "balanced" and profile in {"balanced", "coding_assistant", "analytical"}:
            correct += 1
        elif profile == tc["expected_profile"]:
            correct += 1
        else:
            pass # Failed to route correctly
            
    elapsed = time.time() - start_time
    final_accuracy = (correct / total) * 100
    print("\n" + "="*50)
    print(f"VALIDATION COMPLETE in {elapsed:.1f} seconds")
    print(f"Total Test Cases: {total}")
    print(f"Correctly Routed: {correct}")
    print(f"FINAL ACCURACY: {final_accuracy:.2f}%")
    print("="*50)
    
    return final_accuracy

if __name__ == "__main__":
    # If a command line arg is provided, use that as the number of tests
    num_samples = 50000
    if len(sys.argv) > 1:
        num_samples = int(sys.argv[1])
    run_validation(num_samples)
