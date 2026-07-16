import json
import random
from pathlib import Path

def generate_synthetic_data(num_samples=10000):
    high_verbs = ["explain", "build", "design", "architect", "refactor", "analyze", "debug", "create a comprehensive guide for", "generate code for", "write an extensive document about", "evaluate the performance of", "structure a project for", "implement a scalable solution for", "deploy a secure architecture for"]
    high_topics = [
        "quantum mechanics", "distributed systems", "neural networks", "blockchain", 
        "compiler design", "cryptography", "microservices", "a game called hole.io", 
        "real-time physics engine", "an entire operating system", "string theory",
        "kubernetes orchestration", "large language models", "generative adversarial networks",
        "financial trading algorithms", "autonomous vehicle perception", "medical imaging analysis",
        "global supply chain optimization", "high frequency trading system", "satellite trajectory planning",
        "advanced molecular dynamics simulation", "protein folding prediction", "climate change modeling"
    ]
    high_adverbs = ["in deep detail", "from scratch", "comprehensively", "step by step", "with mathematical proofs", "production ready", "at an advanced level", "for an expert audience", "with strict security compliance", "handling millions of users", "with sub-millisecond latency", "using cutting edge research", "with exhaustive test coverage", "ensuring fault tolerance", "with disaster recovery built in"]
    
    # Templates for MEDIUM complexity
    medium_verbs = ["write a script for", "fix the bug in", "compare", "review", "test", "summarize", "how do I implement", "create a function that does", "set up", "configure", "troubleshoot", "optimize", "document"]
    medium_topics = [
        "python array sorting", "AWS S3 bucket setup", "SQL joins", "React state management", 
        "Docker compose", "CSS grid", "a basic API", "data validation", "user authentication",
        "Redis caching", "JWT tokens", "OAuth2 flow", "MongoDB indexing", "PostgreSQL triggers",
        "Vue.js components", "Angular routing", "Django ORM", "Flask middleware", "Express.js controllers",
        "Nginx reverse proxy", "GitHub actions CI/CD", "Terraform modules", "Ansible playbooks"
    ]
    medium_adverbs = ["quickly", "efficiently", "with standard best practices", "using modern syntax", "for a small team", "in under 100 lines of code", "with basic error handling", "following PEP8", "using async/await", "with clean code principles"]
    
    # Templates for LOW complexity
    low_phrases = ["hello", "how are you", "what is the weather", "good morning", "thanks", "ok", "bye", "who are you", "tell me a joke", "what time is it", "hey there", "sup", "good night", "see ya", "awesome", "cool", "nice", "wow", "can you help me", "I need help", "ping", "test"]
    low_adverbs = ["man", "bro", "friend", "bot", "assistant", "today", "now", "please", "kindly", "buddy", "mate", "dude"]
    
    examples = []
    
    # Generate HIGH complexity examples (~33%)
    for _ in range(int(num_samples * 0.34)):
        text = f"{random.choice(high_verbs)} {random.choice(high_topics)} {random.choice(high_adverbs)}"
        examples.append({
            "text": text,
            "primary_family": random.choice(["coding", "reasoning"]),
            "domain": "general",
            "risk_tier": "high",
            "complexity": "high",
            "risk_type": "standard",
            "expected_output": "free_text",
            "document_type": "generic",
            "decomposition_needed": random.choice([True, False]),
            "needs_verification": random.choice([True, False])
        })
        
    # Generate MEDIUM complexity examples (~33%)
    for _ in range(int(num_samples * 0.33)):
        text = f"{random.choice(medium_verbs)} {random.choice(medium_topics)} {random.choice(medium_adverbs)}"
        examples.append({
            "text": text,
            "primary_family": "coding",
            "domain": "software",
            "risk_tier": "medium",
            "complexity": "medium",
            "risk_type": "standard",
            "expected_output": "code",
            "document_type": "generic",
            "decomposition_needed": False,
            "needs_verification": False
        })
        
    # Generate LOW complexity examples (~33%)
    for _ in range(int(num_samples * 0.33)):
        text = f"{random.choice(low_phrases)} {random.choice(low_adverbs)}" + ("!" * random.randint(0, 2))
        examples.append({
            "text": text,
            "primary_family": "chat",
            "domain": "general",
            "risk_tier": "low",
            "complexity": "low",
            "risk_type": "standard",
            "expected_output": "free_text",
            "document_type": "generic",
            "decomposition_needed": False,
            "needs_verification": False
        })
        
    # Shuffle the dataset
    random.shuffle(examples)
    
    # Append to existing dataset
    dataset_path = Path(__file__).resolve().parents[1] / "data" / "semantic_examples.json"
    if dataset_path.exists():
        with open(dataset_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"version": 2, "examples": []}
        
    data.setdefault("examples", []).extend(examples)
    
    # Ensure no exact duplicates
    unique_texts = set()
    deduped = []
    for ex in data["examples"]:
        if ex["text"] not in unique_texts:
            unique_texts.add(ex["text"])
            deduped.append(ex)
    
    data["examples"] = deduped
    
    with open(dataset_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        
    print(f"Generated {num_samples} new examples. Total dataset size: {len(data['examples'])}")

if __name__ == "__main__":
    generate_synthetic_data(10000)
