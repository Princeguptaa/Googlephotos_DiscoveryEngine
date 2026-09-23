# PRD — AI-Powered Discovery Engine
## Google Photos Retrieval Research Pipeline

## 1. Overview
Build an automated pipeline that:
1. Scrapes public user feedback about Google Photos search/retrieval from 4 sources.
2. Filters it down to relevant items using a keyword list.
3. Classifies each relevant item using Groq's LLM API into a fixed JSON schema.
4. Stores results in a single structured dataset (CSV) for analysis.
5. Validates classification accuracy on a manual sample.

This is a one-time batch research pipeline, not a live/conversational product.

## 2. Data Sources & Collection Method

| # | Source | Method / Tool | Target volume |
|---|--------|---------------|----------------|
| 1 | Google Play Store reviews (Google Photos app) | Python `google-play-scraper` library — pull by app package ID, sort by "most relevant" and "newest", across all star ratings | 450 |
| 2 | Reddit (r/googlephotos + relevant keyword search across Reddit) | Antigravity browser agent — navigate Reddit search results and relevant subreddit/thread pages directly, extract post/comment text, date, and URL (same method as App Store/Forum) | 350 |
| 3 | Apple App Store reviews (Google Photos app) | Browser automation agent — navigate App Store review pages for the Google Photos app, extract review text + rating + date | 150 |
| 4 | Google Photos Community/Support forum | Browser automation agent — navigate relevant threads/pages, extract post text + replies | 250 |

**Total target: ~1200 raw items** (buffer above the 1000 minimum requirement to
account for filtering loss).

Each collected item should be stored with this raw format before filtering:
```
{
  "source": "play_store | reddit | app_store | forum",
  "text": "raw review/post text",
  "date": "YYYY-MM-DD if available, else null",
  "rating": "numeric if available, else null",
  "url": "link to original post if available"
}
```

## 3. Relevance Filter (Cheap Pre-Pass Only)
Keyword matching alone will miss relevant items that describe the problem
without using an obvious keyword (e.g. "I know I have a picture of my old car
loan receipt somewhere but no idea how to dig it up"). So keyword filtering is
used only as a cheap first pass to cut obviously unrelated noise (e.g. pricing
complaints, storage upsell complaints, crash/bug reports) before the more
expensive LLM step — not as the final relevance decision.

Discard an item at this stage ONLY if it clearly matches unrelated topics:
```
storage full, subscription price, crashes, won't open, ads, backup failed,
account locked, payment issue
```

Everything else proceeds to the LLM step, where true relevance is decided
(see Section 4 — `is_relevant` field). Log how many items were dropped at
this pre-pass stage per source (needed for the discovery-engine explainer slide).

## 4. Classification / Tagging Step

**Model/Provider:** Groq API (LLM to be selected within Groq's available free-tier
models — favor a stronger available model for classification quality).

**Process:** For each item that survives the cheap pre-pass, call the Groq API
once with the system prompt below, passing the item's text into the
`{review_text}` placeholder. This single call decides BOTH true relevance and
classification — no separate relevance-check call, to keep cost/complexity low.
Parse the response as JSON and store it alongside the original raw item. If
`is_relevant` is `no`, discard the row (don't populate the rest of the dataset).

**System Prompt (use exactly as written):**
```
Analyze this Google Photos user review or post. Extract only what is explicitly
stated or clearly implied — do not guess or force-fit. Output valid JSON only,
no extra text.

Fields:
- is_relevant: yes / no — is this genuinely about finding/retrieving a photo,
  video, screenshot, or document from memory (not a bug, price, or unrelated complaint)?
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

Review: {review_text}
```

**Output schema (per item, stored as one row):**
```
source, date, rating, url, is_relevant, content_type, retrieval_scenario,
what_they_remembered, what_they_forgot, search_attempt, outcome,
failure_point, workaround_used, evidence_quote
```

## 5. Storage & Output
- Store all tagged rows in a single CSV file (e.g. `tagged_dataset.csv`).
- Also output basic aggregate counts (per `failure_point`, per `content_type`,
  per `source`) as a simple summary table — this will be used directly in the
  problem definition and metric decomposition work.

## 6. Validation Step (Required — do not skip)
- Randomly sample 50–100 tagged rows (only those marked `is_relevant: yes`).
- Manually review these against the original raw text and `evidence_quote` to
  check tagging accuracy, especially for the `failure_point` field (most
  subjective field).
- Report an approximate accuracy percentage and note any systematic
  misclassification patterns.
- This validation result must be simple enough to state in one line on the
  discovery-engine explainer slide (e.g. "~X% agreement with manual review
  on a 75-item sample").

**Note on volume vs. quality:** 1000+ relevant, well-classified rows is the
target floor (set by mentor feedback as a minimum, not optional). Quality is
protected by the `is_relevant` check inside the LLM step itself and this
validation pass — not by lowering the volume target. If usable relevant rows
fall short of 1000 after filtering, scrape additional raw items rather than
relaxing relevance standards.

## 7. Explicit Non-Goals
- No RAG, no conversational interface for this engine.
- No feature recommendations or solution generation — output is data only.
- No assumption of root cause baked into prompts or filters.

## 8. Deliverable From This Build
- A working, re-runnable script/pipeline (source scrape → filter → tag → store).
- A final `tagged_dataset.csv` with ~1000+ usable rows.
- A short aggregate summary (counts by failure_point / content_type / source).
- A brief technical note on how the pipeline works, written simply enough to
  become a single slide explaining the discovery engine.

## 9. Tooling Summary
- **Build/orchestration/scraping:** Antigravity (browser agent for Reddit,
  App Store, and forum; scripts for Play Store)
- **Classification:** Groq API (LLM tagging)
- **Storage:** CSV / simple spreadsheet
- **Secrets needed:** Groq API key (to be provided separately, not hardcoded
  in shared files)
