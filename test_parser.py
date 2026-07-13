import json
from app.core.llm_parser import call_llm_parser

prompt = "generate an image of me playing soccer"

print("Calling LLM Parser...")
try:
    res = call_llm_parser(prompt, [], 10, [])
    print("Parsed Result:")
    print(json.dumps(res.__dict__, indent=2))
except Exception as e:
    print("Error:", e)
