from typing import List
from src.classifier.schema import TaggedItem

def compute_stats(items: List[TaggedItem], pipeline_counts: dict) -> dict:
    """
    Generate summary_stats.json with:
    - by_failure_point (note: multi-label, sums > total)
    - by_content_type
    - by_source
    - total_tagged, total_raw_collected, total_dropped_keyword_filter,
      total_dropped_llm_irrelevant
    """
    stats = {
        "by_failure_point": {},
        "by_content_type": {},
        "by_source": {},
        "by_scenario_type": {},
        "total_tagged": len(items),
        **pipeline_counts  # total_raw, dropped counts
    }
    for item in items:
        # Count failure_points (multi-label)
        for fp in item.failure_point:
            stats["by_failure_point"][fp] = stats["by_failure_point"].get(fp, 0) + 1
        # Count content_type
        ct = item.content_type
        stats["by_content_type"][ct] = stats["by_content_type"].get(ct, 0) + 1
        # Count source
        src = item.source
        stats["by_source"][src] = stats["by_source"].get(src, 0) + 1
        # Count scenario_type
        st = getattr(item, "scenario_type", None)
        if st:
            stats["by_scenario_type"][st] = stats["by_scenario_type"].get(st, 0) + 1
    return stats
