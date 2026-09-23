import csv
from typing import List
from src.classifier.schema import TaggedItem

def write_tagged_csv(items: List[TaggedItem], path: str) -> None:
    """
    Write TaggedItem list to CSV.
    - failure_point list → pipe-delimited string ("expression|refinement")
    - UTF-8 with BOM for Excel compatibility
    - CSV column order matches PRD §4 exactly
    """
    columns = [
        "source", "date", "rating", "url", "is_relevant",
        "content_type", "retrieval_scenario", "what_they_remembered",
        "what_they_forgot", "search_attempt", "outcome",
        "failure_point", "workaround_used", "evidence_quote",
        "scenario_type"
    ]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for item in items:
            row = item.model_dump()
            row["failure_point"] = "|".join(row["failure_point"])
            writer.writerow(row)
