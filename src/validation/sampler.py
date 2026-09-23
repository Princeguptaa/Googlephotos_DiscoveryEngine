import csv
import random

def extract_validation_sample(
    dataset_path: str,
    sample_size: int = 75,
    seed: int = 42,
    output_path: str = "data/validation_sample.csv"
) -> None:
    """
    1. Load tagged_dataset.csv
    2. Filter to rows only (all are is_relevant=yes)
    3. Random sample of sample_size rows (seeded)
    4. Write with same columns + blank "manual_failure_point" column
    """
    random.seed(seed)
    
    with open(dataset_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        # All rows should be is_relevant=yes, but we filter just in case
        rows = [row for row in reader if row.get("is_relevant") == "yes"]
        
    if not rows:
        return
        
    sample = random.sample(rows, min(sample_size, len(rows)))
    
    if not sample:
        return
        
    columns = list(sample[0].keys()) + ["manual_failure_point"]
    
    with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in sample:
            row["manual_failure_point"] = ""
            writer.writerow(row)
