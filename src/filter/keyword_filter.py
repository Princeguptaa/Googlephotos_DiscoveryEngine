import glob
import os
from typing import List, Tuple

from src.classifier.schema import RawItem
from src.utils.io import load_json, save_json
from src.utils.logger import log

EXCLUSION_KEYWORDS = [
    "storage full", "subscription price", "crashes", "won't open",
    "ads", "backup failed", "account locked", "payment issue"
]

def should_exclude(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    return any(kw in text_lower for kw in EXCLUSION_KEYWORDS)

def filter_items(items: List[RawItem]) -> Tuple[List[RawItem], dict]:
    """
    Returns:
        - filtered_items: items that passed the filter
        - stats: dict of { source: { input, dropped, passed } }
    """
    passed = []
    stats = {}
    for item in items:
        src = item.source
        if src not in stats:
            stats[src] = {"input": 0, "dropped": 0, "passed": 0}
        stats[src]["input"] += 1
        if should_exclude(item.text):
            stats[src]["dropped"] += 1
        else:
            stats[src]["passed"] += 1
            passed.append(item)
    return passed, stats

def run_filter(config: dict = None) -> None:
    """Load all raw data, filter, save, and log stats."""
    raw_files = glob.glob("data/raw/*_raw.json")
    if not raw_files:
        log("FILTER", "No raw data files found in data/raw/", "system")
        return
        
    all_items = []
    for file_path in raw_files:
        data = load_json(file_path)
        for item_data in data:
            all_items.append(RawItem(**item_data))
            
    filtered_items, stats = filter_items(all_items)
    
    save_json([item.model_dump() for item in filtered_items], "data/filtered/filtered_items.json")
    
    for src, src_stats in stats.items():
        log("FILTER", f"{src_stats['input']} in -> {src_stats['passed']} passed, {src_stats['dropped']} dropped", src)

if __name__ == "__main__":
    run_filter()
