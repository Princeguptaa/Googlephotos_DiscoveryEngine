import csv
import shutil
import os

def main():
    csv_path = "data/tagged_dataset.csv"
    backup_path = "data/tagged_dataset.before_correction.csv"
    
    # Create backup if not already present
    if not os.path.exists(backup_path):
        shutil.copy2(csv_path, backup_path)
        print(f"Created backup at {backup_path}")

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = list(reader.fieldnames)

    if "scenario_type" not in fieldnames:
        fieldnames.append("scenario_type")

    # The 10 quotes to drop (mark is_relevant = 'no')
    drop_quote_signals = [
        "without actually downloading",          # Row 17: cat photo
        "downloading without",                   # backup match
        "unsupported media",                    # Row 21: download videos
        "missing all my photos from 2017 to 2019", # Row 37
        "all photos taken in the year 2019 have disappeared", # Row 39
        "all but a couple images",               # Row 45: clean up space
        "click download to put them back into my gallery it never works", # Row 67
        "missing album pictures",               # Row 70: Still missing
        "lost god knows how many photos thinking they'd been backed up", # Row 72
        "MY PHOTOS ARE MISSING",                # Row 74
        "video of my two cats"                  # Row 75: no longer has a play availability
    ]

    dropped_indices = []
    
    for i, row in enumerate(rows):
        quote = row.get("evidence_quote", "")
        # Check against signals
        matched_signal = None
        for sig in drop_quote_signals:
            if sig.lower() in quote.lower():
                matched_signal = sig
                break
            # Handle split if ellipsis
            parts = [p.strip() for p in sig.split("...") if p.strip()]
            if len(parts) > 1 and all(p.lower() in quote.lower() for p in parts):
                matched_signal = sig
                break
                
        if matched_signal:
            dropped_indices.append(i)
            row["is_relevant"] = "no"
            row["scenario_type"] = ""
            print(f"Marked row {i+1} as is_relevant: no (signal: '{matched_signal}') | scenario: {row.get('retrieval_scenario')}")
        else:
            row["is_relevant"] = "yes"
            # Classify scenario_type
            # Calibration 1: row with "I have to scroll to find them if I don't know the date" -> vague_memory
            if "if i don't know the date" in quote.lower() or i == 3: # Row 4 (0-indexed 3)
                row["scenario_type"] = "vague_memory"
            else:
                row["scenario_type"] = "general_search_quality"

    print(f"\nTotal rows in dataset: {len(rows)}")
    print(f"Total rows dropped (set is_relevant: no): {len(dropped_indices)}")
    
    relevant_rows = [r for r in rows if r["is_relevant"] == "yes"]
    print(f"Updated total is_relevant: yes count: {len(relevant_rows)}")
    
    vm_count = sum(1 for r in relevant_rows if r["scenario_type"] == "vague_memory")
    gsq_count = sum(1 for r in relevant_rows if r["scenario_type"] == "general_search_quality")
    print(f"vague_memory count: {vm_count}")
    print(f"general_search_quality count: {gsq_count}")

    # Write updated CSV
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"\nSuccessfully wrote updated dataset to {csv_path}")

if __name__ == "__main__":
    main()
