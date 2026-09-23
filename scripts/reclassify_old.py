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
from src.classifier.tagger import item_hash, save_processed_hash, load_already_processed
from src.utils.io import load_prompt
from src.output.csv_writer import write_tagged_csv
from src.utils.logger import log, log_error
from src.classifier.groq_client import GroqClient, GroqTokenLimitReached, GroqClassificationError

def setup_gemini():
    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-3.6-flash')

def classify_with_gemini(model, prompt_template: str, text: str):
    user_msg = prompt_template.replace("{review_text}", text)
    for attempt in range(3):
        try:
            response = model.generate_content(
                user_msg,
                generation_config=genai.types.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.0
                )
            )
            content = response.text.strip()
            result = json.loads(content)
            
            if result.get("is_relevant") == "yes":
                failure_point = result.get("failure_point")
                if failure_point is None or failure_point == "" or failure_point == []:
                    log_error("GEMINI", f"Validation error (Attempt {attempt+1}): failure_point missing")
                    time.sleep(2)
                    continue
            return result
        except Exception as e:
            log_error("GEMINI", f"API Error: {e}")
            time.sleep(2)
    return None

def main():
    load_dotenv()
    log('PIPELINE', "Starting Reclassification of Old Tagged Rows")

    old_csv_path = "data/tagged_dataset.old.csv"
    output_path = "data/tagged_dataset.csv"
    prompt_path = "config/prompts/classification.txt"

    prompt = load_prompt(prompt_path)
    
    # Load all raw items
    from src.utils.io import load_json
    filtered_data = load_json("data/filtered/filtered_items.json")
    all_raw_items = [RawItem(**d) for d in filtered_data]
    
    # Read items from old csv to map back to RawItem
    old_rows = list(csv.DictReader(open(old_csv_path, "r", encoding="utf-8-sig")))
    items_to_reclassify = []
    seen_hashes = set()

    for idx, r in enumerate(old_rows):
        if idx == 0 and r.get('url') == 'http':
            continue  # smoke test mock row
            
        src = r.get('source')
        date = r.get('date')
        rating_str = r.get('rating')
        rating = float(rating_str) if rating_str else None
        url = r.get('url') if r.get('url') else None
        quote = r.get('evidence_quote', '').strip()
        
        match = None
        # 1. Match by URL if present
        if url:
            u_matches = [it for it in all_raw_items if it.url == url]
            if u_matches:
                match = u_matches[0]
                
        # 2. Match by exact (source, date, rating)
        if not match:
            cands = [
                it for it in all_raw_items 
                if it.source == src 
                and it.date == date 
                and (it.rating == rating or (it.rating is None and rating is None))
            ]
            if len(cands) == 1:
                match = cands[0]
            elif len(cands) > 1:
                words = [w.strip('"\'.,?!:;') for w in quote.split() if len(w) > 3]
                match = max(cands, key=lambda it: sum(1 for w in words if w.lower() in it.text.lower()))
            else:
                cands2 = [it for it in all_raw_items if it.source == src and it.date == date]
                if len(cands2) == 1:
                    match = cands2[0]
                elif len(cands2) > 1:
                    words = [w.strip('"\'.,?!:;') for w in quote.split() if len(w) > 3]
                    match = max(cands2, key=lambda it: sum(1 for w in words if w.lower() in it.text.lower()))

        if match:
            h = item_hash(match)
            if h not in seen_hashes:
                items_to_reclassify.append(match)
                seen_hashes.add(h)
        else:
            log_error('PIPELINE', f"Could not match row {idx}: src={src}, date={date}, quote={quote[:30]}")

    log('PIPELINE', f"Loaded {len(items_to_reclassify)} items to re-classify.")

    groq_client = GroqClient(api_key=os.getenv("GROQ_API_KEY"), model="openai/gpt-oss-20b")
    gemini_model = setup_gemini()

    processed_hashes = load_already_processed(output_path)
    
    # Load existing tagged_dataset if any
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

    relevant_count = 0
    irrelevant_count = 0

    for i, item in enumerate(items_to_reclassify):
        ihash = item_hash(item)
        if ihash in processed_hashes:
            continue

        log('PIPELINE', f"Processing item {i+1}/{len(items_to_reclassify)} ({item.source})...")
        
        # Try Groq
        raw_result = None
        try:
            raw_result = groq_client.classify(system_prompt=prompt, user_text=item.text, delay=2.5)
        except GroqTokenLimitReached:
            log_error('PIPELINE', "Groq token limit reached. Stopping.")
            break
        except Exception as e:
            log_error('PIPELINE', f"Groq failed: {e}.")
            if "TPD" in str(e) or "daily" in str(e).lower() or "limit" in str(e).lower():
                log('PIPELINE', "Falling back to Gemini...")
                raw_result = classify_with_gemini(gemini_model, prompt, item.text)
                time.sleep(4.1)
            else:
                continue

        if not raw_result:
            log_error("PIPELINE", f"Failed to classify item {i+1}")
            continue

        save_processed_hash(output_path, ihash)
        processed_hashes.add(ihash)

        if raw_result.get("is_relevant") == "yes":
            relevant_count += 1
            fp = raw_result.get("failure_point")
            if isinstance(fp, str):
                raw_result["failure_point"] = [fp]
            elif not fp:
                raw_result["failure_point"] = ["unknown_unclear"]
            try:
                tagged = TaggedItem(
                    source=item.source,
                    date=item.date,
                    rating=item.rating,
                    url=item.url,
                    **raw_result
                )
                tagged_items.append(tagged)
                write_tagged_csv(tagged_items, output_path)
            except Exception as ve:
                log_error("PIPELINE", f"Validation error on item {i+1}: {ve}")
        else:
            irrelevant_count += 1

    log('PIPELINE', f"Reclassification complete. Processed {relevant_count + irrelevant_count} items.")
    log('PIPELINE', f"Relevant: {relevant_count}, Irrelevant: {irrelevant_count}. Saved {len(tagged_items)} valid items to {output_path}.")

if __name__ == '__main__':
    main()

