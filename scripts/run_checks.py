import csv
import json
import random
from collections import Counter

# 1. Flagged mislabels
def check_mislabels(tagged_rows, filtered_items):
    keywords = ["vanished", "missing after", "stopped working", "corrupted", "backup failed", "sync issue", "bug"]
    flagged_rows = []
    
    for row in tagged_rows:
        evidence_quote = row.get("evidence_quote", "")
        source = row.get("source", "")
        
        # Find original text
        original_text = ""
        for item in filtered_items:
            if item["source"] == source and (evidence_quote in item["text"] or evidence_quote.replace('...', '') in item["text"]):
                original_text = item["text"]
                break
                
        text_to_check = (evidence_quote + " " + original_text).lower()
        has_signal = any(kw in text_to_check for kw in keywords)
        
        if has_signal:
            flagged_rows.append(row)
            
    if flagged_rows:
        with open("data/flagged_for_recheck.csv", "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=tagged_rows[0].keys())
            writer.writeheader()
            writer.writerows(flagged_rows)
            
    print(f"1. Flagged mislabels: Found {len(flagged_rows)} rows. Saved to data/flagged_for_recheck.csv")

# 2. Validation sample
def extract_validation_sample(tagged_rows):
    sample_size = min(35, len(tagged_rows))
    random.seed(42)
    sample = random.sample(tagged_rows, sample_size)
    
    if sample:
        # add manual_failure_point
        fieldnames = list(sample[0].keys()) + ["manual_failure_point"]
        with open("data/validation_sample.csv", "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in sample:
                row["manual_failure_point"] = ""
                writer.writerow(row)
    print(f"2. Validation sample: Extracted {len(sample)} rows into data/validation_sample.csv")

# 3. Schema sanity check
def schema_sanity_check(tagged_rows):
    required_fields = ["source", "is_relevant", "content_type", "retrieval_scenario", 
                       "what_they_remembered", "what_they_forgot", "search_attempt", 
                       "outcome", "failure_point", "workaround_used", "evidence_quote"]
                       
    allowed_fp = ["expression", "system_understanding", "evaluation", "refinement", "unknown_unclear"]
    
    missing_issues = 0
    fp_issues = 0
    
    for row in tagged_rows:
        for rf in required_fields:
            if not row.get(rf) or row.get(rf).strip() == "":
                missing_issues += 1
                
        fp_raw = row.get("failure_point", "")
        if fp_raw:
            fps = fp_raw.split("|")
            for fp in fps:
                if fp not in allowed_fp:
                    fp_issues += 1
        else:
            missing_issues += 1 # failure point empty
            
    print(f"3. Schema check: Found {missing_issues} missing required fields and {fp_issues} invalid failure_point values.")

# 4. Duplicate check
def duplicate_check(tagged_rows):
    quotes = Counter()
    urls = Counter()
    for row in tagged_rows:
        if row.get("evidence_quote"):
            quotes[row["evidence_quote"]] += 1
        if row.get("url"):
            urls[row["url"]] += 1
            
    dup_quotes = sum(1 for v in quotes.values() if v > 1)
    dup_urls = sum(1 for v in urls.values() if v > 1)
    
    print(f"4. Duplicate check: Found {dup_quotes} duplicated evidence_quotes and {dup_urls} duplicated URLs.")

def main():
    with open("data/filtered/filtered_items.json", "r", encoding="utf-8") as f:
        filtered_items = json.load(f)

    with open("data/tagged_dataset.csv", "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        tagged_rows = [row for row in reader if row.get("is_relevant") == "yes"]

    print(f"Processing {len(tagged_rows)} 'is_relevant: yes' rows...")
    print("-" * 50)
    check_mislabels(tagged_rows, filtered_items)
    extract_validation_sample(tagged_rows)
    schema_sanity_check(tagged_rows)
    duplicate_check(tagged_rows)
    print("-" * 50)

if __name__ == "__main__":
    main()
