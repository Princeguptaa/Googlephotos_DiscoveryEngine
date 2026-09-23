from groq import Groq
import time
import json
from src.utils.logger import log_warning

class GroqClassificationError(Exception):
    pass

class GroqTokenLimitReached(Exception):
    pass

class GroqClient:
    def __init__(self, api_key: str, model: str):
        self.client = Groq(api_key=api_key)
        self.model = model
        self.cumulative_tokens = 0

    def classify(self, system_prompt: str, user_text: str,
                 max_retries: int = 100, delay: float = 2.5) -> dict:
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_text}
                    ],
                    temperature=0.0,
                    max_tokens=500,
                    reasoning_effort="low"
                )
                content = response.choices[0].message.content.strip()
                usage = getattr(response, 'usage', None)
                if usage:
                    self.cumulative_tokens += usage.total_tokens
                
                if self.cumulative_tokens > 180000:
                    log_warning("CLASSIFY", f"Groq token limit reached! ({self.cumulative_tokens} tokens). Stopping cleanly.")
                    raise GroqTokenLimitReached(f"Reached {self.cumulative_tokens} tokens")

                if content.startswith("```json"):
                    content = content[7:]
                if content.endswith("```"):
                    content = content[:-3]
                result = json.loads(content.strip())
                time.sleep(delay)
                return result
            except json.JSONDecodeError as e:
                log_warning("CLASSIFY", f"JSON parse error (Attempt {attempt+1}/{max_retries}). Output was: {content[:100]}...")
                time.sleep(delay)
                continue
            except Exception as e:
                error_str = str(e)
                if "429" in error_str:  # Rate limit
                    if "tokens per day (TPD)" in error_str:
                        log_warning("CLASSIFY", f"Daily token limit (TPD) reached! Aborting to prevent silent stall.")
                        raise GroqClassificationError(error_str)
                    wait = 60  # Wait a full minute for token bucket to reset
                    log_warning("CLASSIFY", f"Rate limited (Attempt {attempt+1}/{max_retries}). Waiting {wait}s...")
                    time.sleep(wait)
                elif "50" in error_str: # Server errors
                    if attempt == max_retries - 1:
                        raise GroqClassificationError(error_str)
                    time.sleep(delay)
                else:
                    # 400 or 404 error (e.g. model not found), don't retry 100 times
                    raise GroqClassificationError(error_str)
        raise GroqClassificationError(f"Max retries ({max_retries}) exceeded.")
