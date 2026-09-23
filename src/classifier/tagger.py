import hashlib
import os
from datetime import datetime
from typing import Optional
from pydantic import ValidationError

from src.classifier.schema import RawItem, TaggedItem
from src.classifier.groq_client import GroqClient, GroqClassificationError
from src.utils.io import load_json, save_json
from src.utils.logger import log_error as logger_log_error

def item_hash(item: RawItem) -> str:
    return hashlib.sha256(f"{item.source}:{item.text}".encode()).hexdigest()[:16]

def load_already_processed(csv_path: str) -> set:
    """Load hashes of items already processed to skip on re-run."""
    hash_file = csv_path.replace(".csv", "_hashes.json")
    if not os.path.exists(hash_file):
        return set()
    return set(load_json(hash_file))

def save_processed_hash(csv_path: str, item_hash_str: str) -> None:
    hash_file = csv_path.replace(".csv", "_hashes.json")
    if os.path.exists(hash_file):
        hashes = load_json(hash_file)
    else:
        hashes = []
    hashes.append(item_hash_str)
    save_json(hashes, hash_file)

def log_error(stage, item, error_type, message, raw_response=None):
    """Append error entry to data/error_log.json"""
    error_log_path = "data/error_log.json"
    
    # Also log it to the console logger
    logger_log_error(stage.upper(), f"{error_type}: {message}", item.source)
    
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "stage": stage,
        "source": item.source,
        "item_text_preview": item.text[:100],
        "error_type": error_type,
        "raw_response": str(raw_response) if raw_response else None,
        "error_message": message
    }
    
    # Create parent directory if missing (handled by save_json mostly, but just in case)
    os.makedirs(os.path.dirname(error_log_path), exist_ok=True)
    
    if os.path.exists(error_log_path):
        try:
            logs = load_json(error_log_path)
        except Exception:
            logs = []
    else:
        logs = []
    logs.append(entry)
    save_json(logs, error_log_path)

class Tagger:
    def __init__(self, client: GroqClient, prompt_template: str):
        self.client = client
        self.prompt_template = prompt_template

    def tag(self, item: RawItem, max_retries=3) -> Optional[TaggedItem]:
        # 1. Build user message: inject item.text into prompt template
        user_msg = self.prompt_template.replace("{review_text}", item.text)

        for attempt in range(max_retries):
            # 2. Call Groq API
            try:
                raw_result = self.client.classify(
                    system_prompt=self.prompt_template,
                    user_text=item.text
                )
            except GroqClassificationError as e:
                log_error("classify", item, "api_error", str(e))
                raise e

            # 3. Check is_relevant
            if raw_result.get("is_relevant") == "no":
                return None

            # Explicitly enforce failure_point for relevant items
            failure_point = raw_result.get("failure_point")
            if failure_point is None or failure_point == "" or failure_point == []:
                log_error("classify", item, "missing_field", f"Attempt {attempt+1}/{max_retries}: failure_point missing or empty", raw_result)
                if attempt < max_retries - 1:
                    continue
                return None

            # Normalize failure_point to a list of valid values
            if isinstance(failure_point, str):
                failure_point = [failure_point]
            valid_fps = {"expression", "system_understanding", "evaluation", "refinement", "unknown_unclear"}
            normalized_fps = [fp for fp in failure_point if fp in valid_fps]
            if not normalized_fps:
                normalized_fps = ["unknown_unclear"]
            raw_result["failure_point"] = normalized_fps

            # Normalize outcome
            valid_outcomes = {"found", "gave_up", "found_via_workaround", "not_mentioned"}
            if raw_result.get("outcome") not in valid_outcomes:
                raw_result["outcome"] = "not_mentioned"

            # Normalize content_type
            valid_content_types = {"photo", "screenshot", "document", "video", "not_mentioned"}
            if raw_result.get("content_type") not in valid_content_types:
                raw_result["content_type"] = "not_mentioned"

            # 4. Validate through Pydantic
            try:
                tagged = TaggedItem(
                    source=item.source,
                    date=item.date,
                    rating=item.rating,
                    url=item.url,
                    **raw_result
                )
                return tagged
            except ValidationError as e:
                log_error("classify", item, "validation_error", f"Attempt {attempt+1}/{max_retries}: {str(e)}", raw_result)
                if attempt < max_retries - 1:
                    continue
                return None
