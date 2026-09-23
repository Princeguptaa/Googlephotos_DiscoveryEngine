"""
Google Photos Discovery Engine — Flask Web App
Classifies user reviews/posts through the same pipeline prompt/schema
used in the main classification pipeline, via Groq LLM.
"""

import os
import json
from flask import Flask, render_template, request, jsonify
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# ── Configuration ──────────────────────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")

SYSTEM_PROMPT = """Analyze this Google Photos user review or post. Extract only what is explicitly
stated or clearly implied — do not guess or force-fit. Output valid JSON only,
no extra text.

Fields:
- is_relevant: yes / no — is this genuinely about finding/retrieving a photo,
  video, screenshot, or document from memory? 
  
  CRITICAL RELEVANCE BOUNDARY EXAMPLES:
  Mark `is_relevant: yes` for genuine memory/search struggles where a user is trying to locate a photo they know exists:
  - "search doesn't work like it used to... search by date instead of just names it works perfectly fine"
  - "I end up just having to scroll... the search for any of my Pic is difficult"
  - "Now, for some unknown reason, I can't find it anywhere"
  - "can't find photos I know exist using basic search terms"
  
  Mark `is_relevant: no` for data loss, sync issues, app bugs, or feature complaints where the photo is gone or feature broken:
  - DATA LOSS: "Latest update applied has corrupted my SD card... Opening Google Photos caused my SD card images to be resorted"
  - DATA LOSS: "Google Photos: The Best Photo Application... but all my 2019 photos disappeared"
  - APP BUG: "this thing refuses to upload files now."
  - FEATURE COMPLAINT: "Photos no longer in order after move from iPhone... struggling to find a solution to get favourites folder"
  - FEATURE COMPLAINT: "automatically hide half of your photos... I wish you could turn off, the button that lets you unhide"
- content_type: photo / screenshot / document / video / not_mentioned
- retrieval_scenario: short phrase describing the real situation, e.g.
  "photo from a trip", "screenshot of a payment", "picture of medicine"
- what_they_remembered: short phrase
- what_they_forgot: short phrase
- search_attempt: short phrase or not_mentioned
- outcome: found / gave_up / found_via_workaround / not_mentioned
- failure_point: expression / system_understanding / evaluation / refinement / unknown_unclear
  (choose ALL that clearly apply — this can be a list, not just one value.
  Use "unknown_unclear" rather than guessing if the text doesn't make it clear.)
- workaround_used: short phrase or none
- evidence_quote: the exact short phrase (max ~15 words) from the review that
  best supports the failure_point classification
- scenario_type: vague_memory / general_search_quality (choose which best fits, or null if unclear)"""

# ── Example reviews for quick testing ──────────────────────────────
EXAMPLES = [
    {
        "label": "🔍 Vague Memory Search",
        "text": "I know I took a photo of my dog at the beach last summer but I can't find it no matter what I search. I tried 'dog beach' and 'summer vacation' but nothing comes up. I end up just scrolling through thousands of photos."
    },
    {
        "label": "📸 Screenshot Retrieval",
        "text": "I took a screenshot of a recipe my friend texted me a few months ago. I've been searching 'recipe' and 'food' in Google Photos but it won't show up. Had to ask my friend to send it again."
    },
    {
        "label": "❌ Not Relevant (Data Loss)",
        "text": "After the latest update all my photos from 2019 just disappeared. Google Photos deleted everything and I can't get them back. This app is terrible, I lost years of memories."
    }
]


# ── Routes ─────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html", examples=EXAMPLES)


@app.route("/classify", methods=["POST"])
def classify():
    data = request.get_json()
    review_text = (data or {}).get("review_text", "").strip()

    if not review_text:
        return jsonify({"error": "Please paste a review to classify."}), 400

    if not GROQ_API_KEY:
        return jsonify({"error": "GROQ_API_KEY is not configured on the server."}), 500

    client = Groq(api_key=GROQ_API_KEY)

    candidate_models = [MODEL]
    for fallback in ["openai/gpt-oss-120b", "qwen/qwen3.8-27b"]:
        if fallback not in candidate_models:
            candidate_models.append(fallback)

    last_error = None
    for model_name in candidate_models:
        try:
            kwargs = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": review_text}
                ],
                "temperature": 0.0,
                "max_tokens": 1024,
            }
            if model_name.startswith("openai/gpt-oss"):
                kwargs["reasoning_effort"] = "low"

            response = client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            content = choice.message.content or ""
            content = content.strip()

            if not content:
                continue

            # Strip markdown code fences if present
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]

            result = json.loads(content.strip())

            # Normalize failure_point to list
            fp = result.get("failure_point")
            if isinstance(fp, str):
                result["failure_point"] = [fp]
            elif not isinstance(fp, list):
                result["failure_point"] = ["unknown_unclear"]

            # Ensure scenario_type exists
            if "scenario_type" not in result:
                result["scenario_type"] = None

            return jsonify({"result": result, "model_used": model_name})

        except json.JSONDecodeError as jde:
            last_error = f"JSON decode error with {model_name}: {str(jde)}"
            continue
        except Exception as e:
            last_error = f"Error with {model_name}: {str(e)}"
            # If rate limit or token limit, proceed to next fallback model
            continue

    return jsonify({"error": f"Classification failed across models: {last_error}"}), 500


# ── Local dev entry point ──────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)
