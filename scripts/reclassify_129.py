import os
import sys
import csv
import json
import time
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.classifier.schema import TaggedItem
from src.utils.io import load_json, load_prompt
from src.output.csv_writer import write_tagged_csv
from src.classifier.groq_client import GroqClient, GroqTokenLimitReached
from src.classifier.tagger import Tagger

def find_original_text(filtered_items, row):
    source = row.get("source")
    url = row.get("url")
    evidence_quote = row.get("evidence_quote", "")
    
    # Try by URL first
    if url and url != "N/A":
        for item in filtered_items:
            if item.get("url") == url:
                return item["text"]
                
    # Fallback to evidence quote
    for item in filtered_items:
        if item["source"] == source and (evidence_quote in item["text"] or evidence_quote.replace('...', '') in item["text"]):
            return item["text"]
    return None

def parse_row_to_item(row):
    r = dict(row)
    if "failure_point" in r and isinstance(r["failure_point"], str):
        if r["failure_point"]:
            r["failure_point"] = r["failure_point"].split("|")
        else:
            r["failure_point"] = []
    if r.get("rating"):
        r["rating"] = float(r["rating"])
    else:
        r["rating"] = None
    return TaggedItem(**r)

def main():
    load_dotenv()
    print("Loading datasets...")
    filtered_items = load_json("data/filtered/filtered_items.json")
    
    with open("data/tagged_dataset.csv", "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        tagged_rows = list(reader)

    print(f"Found {len(tagged_rows)} rows to re-classify.")
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        print("GROQ_API_KEY not found.")
        sys.exit(1)
        
    client = GroqClient(api_key=api_key, model="openai/gpt-oss-20b")
    prompt = load_prompt("config/prompts/classification.txt")
    
    new_tagged_items = []
    
    for i, row in enumerate(tagged_rows):
        print(f"Re-classifying item {i+1}/{len(tagged_rows)}...")
        orig_text = find_original_text(filtered_items, row)
        
        if not orig_text:
            print(f"  Warning: Original text not found for row {i+1}. Keeping original classification.")
            new_tagged_items.append(parse_row_to_item(row))
            continue
            
        try:
            result = client.classify(system_prompt=prompt, user_text=orig_text)
        except GroqTokenLimitReached:
            print("  -> Stopped due to token limit.")
            break
        except Exception as e:
            print(f"  Warning: Classification failed for row {i+1}: {e}. Keeping original classification.")
            new_tagged_items.append(parse_row_to_item(row))
            continue
            
        if result.get("is_relevant") == "yes":
            try:
                tagged = TaggedItem(
                    source=row["source"],
                    date=row.get("date"),
                    rating=float(row["rating"]) if row.get("rating") else None,
                    url=row.get("url"),
                    **result
                )
                new_tagged_items.append(tagged)
                print("  -> Kept as relevant.")
            except Exception as e:
                print(f"  Warning: Validation error {e}. Keeping original classification.")
                new_tagged_items.append(parse_row_to_item(row))
        else:
            print("  -> Dropped (is_relevant: no).")
            
        time.sleep(0.5) # Groq rate limits are higher
        
    print(f"Re-classification complete. {len(new_tagged_items)} items remain relevant out of {len(tagged_rows)}.")
    print(f"Cumulative tokens used: {client.cumulative_tokens}")
    
    # Save the new clean dataset
    write_tagged_csv(new_tagged_items, "data/tagged_dataset.csv")
    print("Saved to data/tagged_dataset.csv")

if __name__ == '__main__':
    main()
