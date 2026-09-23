import csv
import json
import os

def main():
    with open("data/filtered/filtered_items.json", "r", encoding="utf-8") as f:
        filtered_items = json.load(f)

    with open("data/tagged_dataset.csv", "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        tagged_rows = list(reader)

    keywords = ["vanished", "missing after", "stopped working", "corrupted", "backup failed", "sync issue", "bug"]

    flagged_rows = []
    
    for row in tagged_rows:
        if row.get("is_relevant", "yes") != "yes":
            continue
            
        evidence_quote = row.get("evidence_quote", "")
        source = row.get("source", "")
        
        # Find the original text
        original_text = ""
        for item in filtered_items:
            # check basic match
            if item["source"] == source and (evidence_quote in item["text"] or evidence_quote.replace('...', '') in item["text"]):
                original_text = item["text"]
                break
                
        text_to_check = (evidence_quote + " " + original_text).lower()
        
        has_signal = any(kw in text_to_check for kw in keywords)
        
        if has_signal:
            flagged_rows.append(row)
            
    print(f"Total existing rows: {len(tagged_rows)}")
    print(f"Flagged rows: {len(flagged_rows)}")
    
    if flagged_rows:
        with open("data/flagged_for_recheck.csv", "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=tagged_rows[0].keys())
            writer.writeheader()
            writer.writerows(flagged_rows)
            
if __name__ == "__main__":
    main()
