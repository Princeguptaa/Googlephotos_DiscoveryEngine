import os
import sys
import csv
import json
import time
from dotenv import load_dotenv
import google.generativeai as genai

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.classifier.schema import RawItem, TaggedItem
from src.classifier.tagger import item_hash, load_already_processed, save_processed_hash
from src.utils.io import load_json, load_prompt
from src.output.csv_writer import write_tagged_csv
from src.utils.logger import log, log_error

def setup_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        log_error("GEMINI", "GEMINI_API_KEY environment variable not set")
        sys.exit(1)
    genai.configure(api_key=api_key)
    # Using gemini-3.6-flash which is fast and supports JSON schema
    model = genai.GenerativeModel('gemini-3.6-flash')
    return model

def classify_with_gemini(model, prompt_template: str, text: str):
    user_msg = prompt_template.replace("{review_text}", text)
    
    # We enforce JSON output natively
    for attempt in range(5):
        try:
            response = model.generate_content(
                user_msg,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.0
                )
            )
            content = response.text.strip()
            
            usage = getattr(response, 'usage_metadata', None)
            tokens_used = usage.total_token_count if usage else 0

            result = json.loads(content)
            
            # Enforce failure_point for relevant items
            if result.get("is_relevant") == "yes":
                failure_point = result.get("failure_point")
                if failure_point is None or failure_point == "" or failure_point == []:
                    log_error("GEMINI", f"Validation error (Attempt {attempt+1}): failure_point is missing or empty")
                    time.sleep(2)
                    continue

            return result, tokens_used
        except json.JSONDecodeError:
            log_error("GEMINI", f"JSON parse error (Attempt {attempt+1})")
            time.sleep(2)
        except Exception as e:
            error_str = str(e)
            if "429" in error_str:
                log_error("GEMINI", f"Rate limited. Waiting 60s...")
                time.sleep(60)
            else:
                log_error("GEMINI", f"API Error: {e}")
                time.sleep(5)
    return None, 0

def run_gemini_fallback():
    load_dotenv()
    log('PIPELINE', "Starting Gemini Fallback Classifier")

    input_path = "data/filtered/filtered_items.json"
    if not os.path.exists(input_path):
        log_error('PIPELINE', f"ERROR: {input_path} not found.")
        return

    filtered_data = load_json(input_path)
    items = [RawItem(**d) for d in filtered_data]

    model = setup_gemini()
    prompt_path = "config/prompts/classification.txt"
    prompt = load_prompt(prompt_path)

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
    newly_tagged = 0
    cumulative_tokens = 0
    
    log('PIPELINE', f"Loaded {len(items)} items. {len(processed_hashes)} already processed.")
    
    for i, item in enumerate(items):
        ihash = item_hash(item)
        if ihash in processed_hashes:
            skipped += 1
            continue

        log('PIPELINE', f"[GEMINI] Processing item {i+1}/{len(items)}...")
        
        raw_result, tokens_used = classify_with_gemini(model, prompt, item.text)
        cumulative_tokens += tokens_used

        if cumulative_tokens > 1000000:  # Arbitrary safe limit for Gemini
            log('PIPELINE', f"[GEMINI] Stopping gracefully due to self-throttle token limit ({cumulative_tokens} tokens).")
            break

        if not raw_result:
            log_error("GEMINI", f"Failed to classify item {i+1}")
            continue
            
        save_processed_hash(output_path, ihash)
        processed_hashes.add(ihash)

        if raw_result.get("is_relevant") == "yes":
            try:
                tagged = TaggedItem(
                    source=item.source,
                    date=item.date,
                    rating=item.rating,
                    url=item.url,
                    **raw_result
                )
                tagged_items.append(tagged)
                newly_tagged += 1
                write_tagged_csv(tagged_items, output_path)
            except Exception as e:
                log_error("GEMINI", f"Validation error on item {i+1}: {e}")
                
        # Sleep to respect 15 RPM limit (1 request every 4 seconds)
        time.sleep(4.1)
        
        if (i + 1) % 150 == 0:
            log('PIPELINE', f"PROGRESS: Processed {i+1} items. Cumulative Gemini tokens: {cumulative_tokens}")

    log('PIPELINE', f"Skipped {skipped} items. {newly_tagged} newly tagged. Total valid: {len(tagged_items)}")
    write_tagged_csv(tagged_items, output_path)

if __name__ == '__main__':
    run_gemini_fallback()
