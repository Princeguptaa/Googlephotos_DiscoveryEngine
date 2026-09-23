import csv
import json
from collections import Counter

def main():
    # Load original texts
    with open("data/filtered/filtered_items.json", "r", encoding="utf-8") as f:
        filtered_items = json.load(f)
        
    def find_original_text(source, evidence_quote):
        for item in filtered_items:
            if item["source"] == source and (evidence_quote in item["text"] or evidence_quote.replace('...', '') in item["text"]):
                return item["text"]
        return "Not found"

    with open("data/tagged_dataset.csv", "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        tagged_rows = list(reader)

    required_fields = ["source", "is_relevant", "content_type", "retrieval_scenario", 
                       "what_they_remembered", "what_they_forgot", "search_attempt", 
                       "outcome", "failure_point", "workaround_used", "evidence_quote"]
                       
    defaults = {
        "content_type": "not_mentioned",
        "search_attempt": "not_mentioned",
        "outcome": "not_mentioned",
        "workaround_used": "none",
        "failure_point": "unknown_unclear"
    }

    print("--- MISSING FIELDS PATCHING ---")
    patched_count = 0
    for i, row in enumerate(tagged_rows):
        if row.get("is_relevant") != "yes":
            continue
            
        for rf in required_fields:
            if not row.get(rf) or str(row.get(rf)).strip() == "":
                if rf in defaults:
                    print(f"Row {i} missing '{rf}'. Patching to '{defaults[rf]}'")
                    row[rf] = defaults[rf]
                    patched_count += 1
                else:
                    print(f"Row {i} missing '{rf}' but no safe default exists!")
                    
    if patched_count > 0:
        with open("data/tagged_dataset.csv", "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=tagged_rows[0].keys())
            writer.writeheader()
            writer.writerows(tagged_rows)
        print(f"Successfully patched and saved {patched_count} fields.\n")
        
    print("--- DUPLICATE EVIDENCE QUOTE INVESTIGATION ---")
    quotes = Counter()
    for row in tagged_rows:
        if row.get("is_relevant") == "yes" and row.get("evidence_quote"):
            quotes[row["evidence_quote"]] += 1
            
    dup_quote = None
    for q, count in quotes.items():
        if count > 1:
            dup_quote = q
            break
            
    if dup_quote:
        print(f"Duplicate Quote: '{dup_quote}'\n")
        
        matches = [row for row in tagged_rows if row.get("is_relevant") == "yes" and row.get("evidence_quote") == dup_quote]
        for idx, match in enumerate(matches):
            orig_text = find_original_text(match["source"], dup_quote)
            print(f"Match {idx + 1}:")
            print(f"Source: {match.get('source')}")
            print(f"URL: {match.get('url', 'N/A')}")
            print(f"Original Text: {orig_text}")
            print("-" * 40)
    else:
        print("No duplicate quote found.")

if __name__ == "__main__":
    main()
