import json
import logging
import os
import sys
import yaml

# Setup basic logging
logging.basicConfig(level=logging.INFO)

from src.classifier.tagger import Tagger
from src.classifier.schema import RawItem
from src.classifier.groq_client import GroqClient

def run_smoke_test():
    with open("config/settings.yaml", "r") as f:
        settings = yaml.safe_load(f)
        
    model_name = settings["classifier"]["model"]
    prompt_file = settings["classifier"]["prompt_file"]
    
    with open(prompt_file, "r") as f:
        prompt_template = f.read()

    from dotenv import load_dotenv
    load_dotenv()
    
    api_key = os.environ.get("GROQ_API_KEY", "")
    client = GroqClient(api_key=api_key, model=model_name)
    tagger = Tagger(client=client, prompt_template=prompt_template)
    
    # Check if filtered items exist
    input_file = "data/filtered/filtered_items.json"
    if not os.path.exists(input_file):
        print(f"File not found: {input_file}")
        return
        
    with open(input_file, "r", encoding="utf-8") as f:
        items_data = json.load(f)
        
    if not items_data:
        print("No items in filtered_items.json")
        return
        
    # Test just the first item
    first_item = items_data[0]
    raw_item = RawItem(**first_item)
    
    print(f"Testing model: {model_name}")
    print(f"Sending item: {raw_item.source} - {raw_item.text[:50]}...")
    
    # Process it directly via client to see raw JSON output
    raw_result = client.classify(
        system_prompt=prompt_template,
        user_text=raw_item.text
    )
    
    print("\n--- Raw Result JSON from Groq ---")
    print(json.dumps(raw_result, indent=2))
    print("Smoke test PASSED! Returns valid JSON and format.")

if __name__ == "__main__":
    run_smoke_test()
