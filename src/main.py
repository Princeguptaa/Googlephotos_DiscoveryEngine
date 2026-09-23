import argparse
import os
import csv

from src.utils.logger import log, log_error
from src.utils.io import load_config, load_json, save_json, load_prompt
from src.classifier.schema import RawItem, TaggedItem


def run_collect(config: dict):
    from src.collectors.play_store import PlayStoreCollector
    from src.collectors.reddit import RedditCollector
    from src.collectors.app_store import AppStoreCollector
    from src.collectors.forum import ForumCollector

    log('PIPELINE', "Starting collect stage")
    collection_config = config.get("collection", {})
    targets = {k: v.get("target_volume", 0) for k, v in collection_config.items()}

    collectors = {
        "play_store": PlayStoreCollector(),
        "reddit": RedditCollector(),
        "app_store": AppStoreCollector(),
        "forum": ForumCollector()
    }

    for source, target in targets.items():
        if source in collectors:
            log('PIPELINE', f"Collecting from {source} (target: {target})...")
            items = collectors[source].collect(target)
            collectors[source].save(items, f"data/raw/{source}_raw.json")
            log('PIPELINE', f"Saved {len(items)} items to data/raw/{source}_raw.json")


def run_filter(config: dict):
    from src.filter.keyword_filter import filter_items
    
    log('PIPELINE', "Starting filter stage")

    all_raw = []
    sources = ["play_store", "reddit", "app_store", "forum"]
    for src in sources:
        path = f"data/raw/{src}_raw.json"
        if not os.path.exists(path):
            log_error('PIPELINE', f"ERROR: {path} not found. Run --stage collect first.")
            return
        data = load_json(path)
        all_raw.extend([RawItem(**d) for d in data])

    passed, stats = filter_items(all_raw)

    save_json([item.model_dump() for item in passed], "data/filtered/filtered_items.json")

    for src, stat in stats.items():
        log('PIPELINE', f"[FILTER] {src}: {stat['input']} in -> {stat['passed']} passed, {stat['dropped']} dropped")


def run_classify(config: dict):
    from src.classifier.groq_client import GroqClient, GroqTokenLimitReached, GroqClassificationError
    from src.classifier.tagger import Tagger, load_already_processed, save_processed_hash, item_hash
    from src.output.csv_writer import write_tagged_csv

    log('PIPELINE', "Starting classify stage")

    input_path = "data/filtered/filtered_items.json"
    if not os.path.exists(input_path):
        log_error('PIPELINE', f"ERROR: {input_path} not found. Run --stage filter first.")
        return

    filtered_data = load_json(input_path)
    items = [RawItem(**d) for d in filtered_data]

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        log_error('PIPELINE', "GROQ_API_KEY environment variable not set")
        return

    classifier_config = config.get("classifier", {})
    client = GroqClient(api_key=api_key, model=classifier_config.get("model", "openai/gpt-oss-20b"))

    prompt_path = classifier_config.get("prompt_path", "config/prompts/classification.txt")
    prompt = load_prompt(prompt_path)

    tagger = Tagger(client, prompt)

    output_path = "data/tagged_dataset.csv"
    processed_hashes = load_already_processed(output_path)

    tagged_items = []
    if os.path.exists(output_path):
        with open(output_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if "failure_point" in row and row["failure_point"]:
                    row["failure_point"] = row["failure_point"].split("|")
                else:
                    row["failure_point"] = []
                if "manual_failure_point" in row:
                    del row["manual_failure_point"]
                if row.get("rating"):
                    row["rating"] = float(row["rating"])
                else:
                    row["rating"] = None
                tagged_items.append(TaggedItem(**row))

    skipped = 0
    log('PIPELINE', f"Loaded {len(items)} items to classify. {len(processed_hashes)} already processed.")
    newly_tagged = 0
    processed_in_run = 0
    for i, item in enumerate(items):
        ihash = item_hash(item)
        if ihash in processed_hashes:
            skipped += 1
            continue

        log('PIPELINE', f"[CLASSIFY] Processing item {i+1}/{len(items)} ({item.source})...")
        try:
            tagged = tagger.tag(item)
        except GroqTokenLimitReached:
            log('PIPELINE', "[CLASSIFY] Stopping gracefully due to Groq self-throttle token limit (~180k tokens).")
            break
        except GroqClassificationError as e:
            log_error('PIPELINE', f"[CLASSIFY] Stopping gracefully due to Groq daily limit / error: {e}")
            break

        save_processed_hash(output_path, ihash)
        processed_hashes.add(ihash)
        processed_in_run += 1

        if tagged:
            tagged_items.append(tagged)
            newly_tagged += 1
            # Write incrementally to save progress
            write_tagged_csv(tagged_items, output_path)

        if (i + 1) % 50 == 0:
            log('PIPELINE', f"PROGRESS: Processed {i+1}/{len(items)} items ({processed_in_run} in this run). Cumulative Groq tokens: {client.cumulative_tokens}")

    if skipped > 0:
        log('PIPELINE', f"Skipped {skipped} already-processed items")

    log('PIPELINE', f"[CLASSIFY] Finished. {processed_in_run} processed in this run, {newly_tagged} newly tagged as relevant. Total tagged in dataset: {len(tagged_items)}")
    write_tagged_csv(tagged_items, output_path)

    import sys
    if len(processed_hashes) < len(items):
        log('PIPELINE', f"[CLASSIFY] {len(items) - len(processed_hashes)} items remaining. Exiting with code 2 for retry.")
        sys.exit(2)

def run_output(config: dict):
    from src.output.stats import compute_stats

    log('PIPELINE', "Starting output stage")
    output_path = "data/tagged_dataset.csv"
    if not os.path.exists(output_path):
        log_error('PIPELINE', f"ERROR: {output_path} not found. Run --stage classify first.")
        return

    tagged_items = []
    with open(output_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("is_relevant") != "yes":
                continue
            if "failure_point" in row and row["failure_point"]:
                row["failure_point"] = row["failure_point"].split("|")
            else:
                row["failure_point"] = []
            if "manual_failure_point" in row:
                del row["manual_failure_point"]
            if row.get("rating"):
                row["rating"] = float(row["rating"])
            else:
                row["rating"] = None
            tagged_items.append(TaggedItem(**row))

    pipeline_counts = {
        "total_raw_collected": 0,
        "total_dropped_keyword_filter": 0,
        "total_dropped_llm_irrelevant": 0
    }

    for src in ["play_store", "reddit", "app_store", "forum"]:
        p = f"data/raw/{src}_raw.json"
        if os.path.exists(p):
            pipeline_counts["total_raw_collected"] += len(load_json(p))

    filtered_path = "data/filtered/filtered_items.json"
    if os.path.exists(filtered_path):
        filtered_count = len(load_json(filtered_path))
        pipeline_counts["total_dropped_keyword_filter"] = pipeline_counts["total_raw_collected"] - filtered_count

        hash_file = output_path.replace(".csv", "_hashes.json")
        processed = len(load_json(hash_file)) if os.path.exists(hash_file) else 0

        pipeline_counts["total_dropped_llm_irrelevant"] = processed - len(tagged_items)

    stats = compute_stats(tagged_items, pipeline_counts)
    save_json(stats, "data/summary_stats.json")
    log('PIPELINE', "Saved data/summary_stats.json")


def run_validate(config: dict):
    from src.validation.sampler import extract_validation_sample
    
    log('PIPELINE', "Starting validate stage")

    output_path = "data/tagged_dataset.csv"
    if not os.path.exists(output_path):
        log_error('PIPELINE', f"ERROR: {output_path} not found. Run --stage classify first.")
        return

    val_config = config.get("validation", {})
    extract_validation_sample(
        dataset_path=output_path,
        sample_size=val_config.get("sample_size", 75),
        seed=val_config.get("random_seed", 42)
    )
    log('PIPELINE', "Saved data/validation_sample.csv")


def main():
    parser = argparse.ArgumentParser(description="Discovery Engine Pipeline")
    parser.add_argument("--stage", choices=[
        "collect", "filter", "classify", "output", "validate", "all"
    ], default="all")
    args = parser.parse_args()

    config = load_config()

    if args.stage in ("collect", "all"):
        run_collect(config)

    if args.stage in ("filter", "all"):
        run_filter(config)

    if args.stage in ("classify", "all"):
        run_classify(config)

    if args.stage in ("output", "all"):
        run_output(config)

    if args.stage in ("validate", "all"):
        run_validate(config)

    log('PIPELINE', "Pipeline complete.")

if __name__ == "__main__":
    main()
