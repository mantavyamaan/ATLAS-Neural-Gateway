import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import time
from app.core.embedding_parser import get_parser

def run_tests():
    print("Loading Parser (this will trigger ONNX and download the model if needed)...")
    start = time.time()
    parser = get_parser()
    print(f"Loaded in {time.time() - start:.3f}s")
    
    test_cases = [
        ("write a script to scrape data from wikipedia", "coding"),
        ("hello how are you doing", "chat"),
        ("my chest hurts really bad should I go to hospital?", "chat"),
        ("extract details from this invoice", "ocr"),
        ("how to drop table users", "chat") # Should be safely overridden to operational risk
    ]
    
    latencies = []
    
    for prompt, expected_family in test_cases:
        start = time.time()
        parse = parser.parse(prompt)
        lat = (time.time() - start) * 1000
        latencies.append(lat)
        
        print(f"\nPrompt: '{prompt}'")
        print(f"Latency: {lat:.1f}ms")
        print(f"Family: {parse.primary_family}")
        print(f"Risk: {parse.risk_tier}")
        print(f"Domain: {parse.domain}")
        print(f"Ambiguity: {parse.ambiguity_score}")
        
    print(f"\nAverage Latency: {sum(latencies)/len(latencies):.2f}ms")

if __name__ == "__main__":
    run_tests()
