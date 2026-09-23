# Edge Cases & Corner Scenarios
## AI-Powered Discovery Engine — Google Photos Retrieval Pipeline

> This document catalogs every known corner scenario across all pipeline stages.
> Each edge case includes: what triggers it, which module is affected, the
> expected behavior, and a concrete example where applicable.
>
> **Use this as a testing checklist during each implementation phase.**

---

## Table of Contents

1. [Stage 1 — Collection Edge Cases](#1-stage-1--collection-edge-cases)
2. [Stage 2 — Keyword Filter Edge Cases](#2-stage-2--keyword-filter-edge-cases)
3. [Stage 3 — LLM Classification Edge Cases](#3-stage-3--llm-classification-edge-cases)
4. [Stage 4 — Output & Serialization Edge Cases](#4-stage-4--output--serialization-edge-cases)
5. [Pipeline Orchestration Edge Cases](#5-pipeline-orchestration-edge-cases)
6. [Data Quality & Schema Edge Cases](#6-data-quality--schema-edge-cases)
7. [Environment & Configuration Edge Cases](#7-environment--configuration-edge-cases)

---

## 1. Stage 1 — Collection Edge Cases

### EC-1.1 — Empty or missing reviews from Play Store

| Attribute | Detail |
|-----------|--------|
| **Trigger** | `google-play-scraper` returns an empty list or raises an exception (e.g. Google changes the page structure, network timeout, regional blocking). |
| **Module** | `src/collectors/play_store.py` |
| **Expected behavior** | Log a warning with the actual count vs. target. Write an empty `play_store_raw.json` array. Pipeline continues — other sources still contribute. |
| **Risk** | Play Store is the largest source (450 target). If it returns 0, hitting the 1000-item floor depends entirely on other sources. |

### EC-1.2 — Play Store returns duplicate reviews across sort orders

| Attribute | Detail |
|-----------|--------|
| **Trigger** | Fetching with `Sort.MOST_RELEVANT` and then `Sort.NEWEST` returns overlapping reviews (same user, same text). |
| **Module** | `src/collectors/play_store.py` |
| **Expected behavior** | Deduplicate by review text hash before saving. Log how many dupes were removed. |
| **Example** | A highly-upvoted review appears in both "most relevant" and "newest" result pages. |

### EC-1.3 — Reddit post with empty body text (title-only posts)

| Attribute | Detail |
|-----------|--------|
| **Trigger** | Many Reddit posts are link posts or image posts with a title but `selftext == ""`. |
| **Module** | `src/collectors/reddit.py` |
| **Expected behavior** | Use the **title** as the `text` field if `selftext` is empty. If both title and selftext are empty/null, skip the item and log it. |
| **Example** | `"Google Photos can't find my vacation pics"` (title only, no body). |

### EC-1.4 — Reddit comment is [deleted] or [removed]

| Attribute | Detail |
|-----------|--------|
| **Trigger** | Browser agent encounters comments where the displayed text is "[deleted]" or "[removed]". |
| **Module** | `src/collectors/reddit.py` |
| **Expected behavior** | Skip these comments entirely. Do not count them toward `target_volume`. |

### EC-1.5 — Reddit rate limiting or anti-bot detection

| Attribute | Detail |
|-----------|--------|
| **Trigger** | Reddit serves a rate-limit page, CAPTCHA, or "Too Many Requests" response during browser-agent scraping. |
| **Module** | `src/collectors/reddit.py` |
| **Expected behavior** | Browser agent should pause (60–120 seconds) and retry. If persistent, log warning and return partial results. Operator can re-run `--stage collect` later. |

### EC-1.6 — Apple RSS feed returns HTTP 403 or empty feed

| Attribute | Detail |
|-----------|--------|
| **Trigger** | Apple blocks the request (geo-restriction, rate limit, or temporary outage), or the app has no reviews in that country. |
| **Module** | `src/collectors/app_store.py` |
| **Expected behavior** | Log the failed country code. Continue fetching from remaining countries. If all countries fail, invoke browser fallback (if `fallback_to_browser: true` in config). |
| **Example** | `https://itunes.apple.com/au/rss/customerreviews/id=962194608/...` returns 403 from certain IP ranges. |

### EC-1.7 — Apple RSS JSON structure differs from expected schema

| Attribute | Detail |
|-----------|--------|
| **Trigger** | Apple changes the RSS JSON format — e.g. `entry` key is renamed, `im:rating` path changes, or the feed returns XML instead of JSON. |
| **Module** | `src/collectors/app_store.py` |
| **Expected behavior** | Wrap JSON parsing in try/except. If the structure is unrecognizable, log the raw response to `data/error_log.json` with `error_type: "rss_schema_mismatch"`, and fall back to browser agent. |

### EC-1.8 — Apple RSS feed has no `entry` key (app with 0 reviews)

| Attribute | Detail |
|-----------|--------|
| **Trigger** | A country feed for a niche app might return a valid JSON response but with no `entry` array (only `feed.author`, `feed.title`). |
| **Module** | `src/collectors/app_store.py` |
| **Expected behavior** | Check `if "entry" not in feed_data.get("feed", {})`. Log and skip that country — not an error, just no data. |

### EC-1.9 — Apple RSS returns a single entry as a dict instead of a list

| Attribute | Detail |
|-----------|--------|
| **Trigger** | When a country feed has exactly 1 review, Apple's JSON may return `entry` as a single object `{}` instead of a list `[{}]`. |
| **Module** | `src/collectors/app_store.py` |
| **Expected behavior** | Normalize: `if isinstance(entries, dict): entries = [entries]` before iterating. |

### EC-1.10 — Forum browser stub runs before AGY populates the file

| Attribute | Detail |
|-----------|--------|
| **Trigger** | `python -m src.main` runs the collect stage but `data/raw/forum_raw.json` does not exist (AGY browser agent hasn't run yet). |
| **Module** | `src/collectors/forum.py` |
| **Expected behavior** | Return an empty list. Log warning: `"Forum data file not found. Run browser agent to populate."`. Pipeline continues without forum data. |

### EC-1.11 — Non-English reviews in multi-country RSS feeds

| Attribute | Detail |
|-----------|--------|
| **Trigger** | Fetching from `in`, `gb`, etc. may return reviews in Hindi, Tamil, or other languages. |
| **Module** | `src/collectors/app_store.py` |
| **Expected behavior** | **Keep them.** The LLM (Groq) can process multilingual text. The `is_relevant` check will naturally filter out items it can't parse. Do NOT pre-filter by language. |

### EC-1.12 — Review text exceeds LLM context limit

| Attribute | Detail |
|-----------|--------|
| **Trigger** | A Reddit post or forum thread is extremely long (>10,000 tokens). Groq's context window is 128k so this is unlikely, but the system prompt + review text together could theoretically approach it. |
| **Module** | `src/collectors/reddit.py`, `src/classifier/tagger.py` |
| **Expected behavior** | Truncate `text` to a safe max (e.g. 8,000 characters ≈ ~2,000 tokens) at collection time. Log truncation. |

### EC-1.13 — Collector returns more items than `target_volume`

| Attribute | Detail |
|-----------|--------|
| **Trigger** | Pagination or multi-sort fetching produces more results than requested. |
| **Module** | All collectors |
| **Expected behavior** | Slice to `target_volume` after deduplication. Do NOT silently discard — log: `"Collected 523, trimmed to target 450."` |

---

## 2. Stage 2 — Keyword Filter Edge Cases

### EC-2.1 — Review text contains an exclusion keyword inside a relevant context

| Attribute | Detail |
|-----------|--------|
| **Trigger** | A review says: `"The app won't open my search results properly when I look for old photos"` — contains `"won't open"` but is actually relevant. |
| **Module** | `src/filter/keyword_filter.py` |
| **Expected behavior** | This item **will** be dropped (false positive). **This is an accepted trade-off.** The PRD mandates the filter be narrow (only 8 terms). If this becomes a pattern visible in drop counts, expand the exclusion to require surrounding context (e.g. `"app won't open"` vs just `"won't open"`). |
| **Mitigation** | Monitor false-positive rate during Phase 3 checkpoint. |

### EC-2.2 — Review text is empty or whitespace-only

| Attribute | Detail |
|-----------|--------|
| **Trigger** | A malformed raw item has `text: ""` or `text: "   "`. |
| **Module** | `src/filter/keyword_filter.py` |
| **Expected behavior** | `should_exclude("")` returns `False` (no keyword match), so it passes the filter. But it should be caught earlier — add a check: **drop items where `text.strip()` is empty** before running the keyword filter. Log these separately. |

### EC-2.3 — Exclusion keyword appears in a non-English review

| Attribute | Detail |
|-----------|--------|
| **Trigger** | A review in French contains the English word `"ads"` as part of a French word (e.g., `"les grands"` — false match is unlikely here, but `"ads"` could appear as a fragment in transliterated text). |
| **Module** | `src/filter/keyword_filter.py` |
| **Expected behavior** | Current filter uses `in` (substring match), which could produce false positives on very short keywords like `"ads"`. Accept this risk — the keyword list is intentionally conservative and short. |

### EC-2.4 — All items from one source are filtered out

| Attribute | Detail |
|-----------|--------|
| **Trigger** | If a source's reviews are dominated by unrelated complaints (e.g. every Play Store review mentions "ads"), the filter could drop all 450 items. |
| **Module** | `src/filter/keyword_filter.py` |
| **Expected behavior** | Log a `WARNING` if a source drops >80% of its items. This signals the keyword list may be too aggressive for that source, or the source itself is not useful. Pipeline continues. |

### EC-2.5 — Exclusion keyword with special characters or Unicode

| Attribute | Detail |
|-----------|--------|
| **Trigger** | Review text containing `"won't open"` with a Unicode curly apostrophe (`\u2019`) instead of ASCII `'`. |
| **Module** | `src/filter/keyword_filter.py` |
| **Expected behavior** | Normalize apostrophes before matching: `text.replace("\u2018", "'").replace("\u2019", "'")`. Otherwise `"won\u2019t open"` would bypass the `"won't open"` exclusion keyword. |

---

## 3. Stage 3 — LLM Classification Edge Cases

### EC-3.1 — LLM returns valid JSON but with extra/unexpected fields

| Attribute | Detail |
|-----------|--------|
| **Trigger** | The model returns `{"is_relevant": "yes", "confidence": 0.9, ...}` — includes a field (`confidence`) not in the schema. |
| **Module** | `src/classifier/tagger.py`, `src/classifier/schema.py` |
| **Expected behavior** | Pydantic `BaseModel` with default config **ignores** extra fields. The extra field is silently dropped. This is correct behavior — no error needed. |

### EC-3.2 — LLM returns `failure_point` as a string instead of a list

| Attribute | Detail |
|-----------|--------|
| **Trigger** | Model outputs `"failure_point": "expression"` instead of `"failure_point": ["expression"]`. |
| **Module** | `src/classifier/tagger.py` |
| **Expected behavior** | Before Pydantic validation, normalize: `if isinstance(result["failure_point"], str): result["failure_point"] = [result["failure_point"]]`. This is the **most likely LLM formatting error** — handle it proactively. |

### EC-3.3 — LLM returns `is_relevant: "no"` with partially filled fields

| Attribute | Detail |
|-----------|--------|
| **Trigger** | Model outputs `{"is_relevant": "no", "content_type": "photo", "retrieval_scenario": "trip photo", ...}` — the item is irrelevant but other fields are populated. |
| **Module** | `src/classifier/tagger.py` |
| **Expected behavior** | Check `is_relevant` **first**, before Pydantic validation. If `"no"`, return `None` immediately — do not validate or store the other fields. |

### EC-3.4 — LLM returns `is_relevant` with unexpected casing or value

| Attribute | Detail |
|-----------|--------|
| **Trigger** | Model returns `"is_relevant": "Yes"` or `"is_relevant": "YES"` or `"is_relevant": true` (boolean instead of string). |
| **Module** | `src/classifier/tagger.py` |
| **Expected behavior** | Normalize before validation: `str(value).lower().strip()`. Convert boolean `True` → `"yes"` and `False` → `"no"`. |

### EC-3.5 — LLM returns an outcome value not in the schema

| Attribute | Detail |
|-----------|--------|
| **Trigger** | Model returns `"outcome": "partially_found"` or `"outcome": "unclear"` — not in the `Literal["found", "gave_up", "found_via_workaround", "not_mentioned"]` enum. |
| **Module** | `src/classifier/schema.py` |
| **Expected behavior** | Pydantic raises `ValidationError`. Log to `error_log.json` with the raw response. Skip the item. |
| **Frequency** | Rare with `temperature=0.0` and `json_mode`, but possible. |

### EC-3.6 — LLM returns `evidence_quote` that doesn't appear in the source text

| Attribute | Detail |
|-----------|--------|
| **Trigger** | The model paraphrases or fabricates the quote instead of extracting verbatim text. |
| **Module** | `src/classifier/tagger.py` |
| **Expected behavior** | **No automated check at classification time** (substring matching is fragile with punctuation/spacing differences). Flag this in the **validation step** (Phase 5) — the human reviewer should check that `evidence_quote` ≈ appears in the raw text. Document the hallucination rate. |

### EC-3.7 — LLM returns empty string for required fields

| Attribute | Detail |
|-----------|--------|
| **Trigger** | Model returns `"retrieval_scenario": ""` or `"what_they_remembered": ""`. These are `str` type — empty string passes Pydantic validation. |
| **Module** | `src/classifier/tagger.py` |
| **Expected behavior** | Add a post-validation check: if any text field (except `workaround_used`) is empty, log a warning but **keep the item**. Empty fields are better than dropped items. The validation sample will catch systematic emptiness. |

### EC-3.8 — Groq API returns non-JSON response despite `json_mode`

| Attribute | Detail |
|-----------|--------|
| **Trigger** | Extremely rare with `response_format={"type": "json_object"}`, but possible during model instability or when the model prepends text before JSON (e.g. `"Here's the analysis: {..."}`). |
| **Module** | `src/classifier/groq_client.py` |
| **Expected behavior** | `json.loads()` raises `JSONDecodeError`. Retry once. If still fails, try to extract JSON from the response using a regex (`r'\{.*\}'` with `re.DOTALL`). If that also fails, log and skip. |

### EC-3.9 — Groq daily token limit exhausted mid-classification

| Attribute | Detail |
|-----------|--------|
| **Trigger** | `openai/gpt-oss-120b` has ~100k daily token limit. With ~1100 items and ~300 tokens/call (prompt + response), total is ~330k tokens — exceeds daily limit. |
| **Module** | `src/classifier/groq_client.py` |
| **Expected behavior** | The API will return 429 with a message about daily limits. Log the error. **The resume logic (hash-based dedup) ensures re-running the next day picks up where it left off.** Alternatively, switch model to `meta-llama/llama-4-scout-17b` (500k TPD) in `settings.yaml`. |
| **Risk** | **High.** This is the most likely blocker for a single-day full run with the 70B model. |

### EC-3.10 — Classification of ambiguous / borderline-relevant items

| Attribute | Detail |
|-----------|--------|
| **Trigger** | Review text describes a search struggle but for a **different app** (e.g. "I can't find my photos in iCloud either, moved to Google Photos and same problem"). |
| **Module** | LLM prompt design |
| **Expected behavior** | The LLM should mark `is_relevant: "yes"` if the complaint is about **Google Photos search/retrieval** specifically. If the complaint is about another service, it should be `"no"`. The prompt says "Google Photos user review" — this anchors context. Edge cases caught in validation. |

### EC-3.11 — LLM returns `failure_point: ["unknown_unclear"]` for most items

| Attribute | Detail |
|-----------|--------|
| **Trigger** | The model defaults to `unknown_unclear` when the text is vague, producing an uninformative dataset. |
| **Module** | `src/classifier/tagger.py`, validation step |
| **Expected behavior** | If >30% of items are `unknown_unclear`-only, this is a **signal to iterate on the prompt** — not a code bug. The validation sample (Phase 5) will surface this pattern. Document it. |

### EC-3.12 — Identical review text appears across multiple sources

| Attribute | Detail |
|-----------|--------|
| **Trigger** | A user posts the same complaint on Reddit and Google Community forum. Both are collected. |
| **Module** | `src/classifier/tagger.py` |
| **Expected behavior** | **Do NOT deduplicate across sources.** Each is a separate data point from a different channel. The `source` field distinguishes them. The LLM may classify them identically, which is correct. |

### EC-3.13 — Review text is in a non-English language

| Attribute | Detail |
|-----------|--------|
| **Trigger** | RSS feeds from `in`, `gb` may return Hindi, Urdu, or other language reviews. Reddit may have non-English posts. |
| **Module** | `src/classifier/tagger.py` |
| **Expected behavior** | The LLM handles multilingual input. If it cannot parse the text, it should return `is_relevant: "no"`. Do not pre-filter by language — let the model decide. |

---

## 4. Stage 4 — Output & Serialization Edge Cases

### EC-4.1 — `failure_point` list with multiple values in CSV

| Attribute | Detail |
|-----------|--------|
| **Trigger** | `failure_point: ["expression", "system_understanding"]` must be serialized to CSV. |
| **Module** | `src/output/csv_writer.py` |
| **Expected behavior** | Pipe-delimited: `"expression|system_understanding"`. Not JSON array syntax. Verify Excel/Sheets correctly reads this as a single cell, not two columns. |

### EC-4.2 — Review text contains commas, newlines, or double quotes

| Attribute | Detail |
|-----------|--------|
| **Trigger** | Raw text: `"I searched for "my dog" but found nothing, even after scrolling\nthrough hundreds of results"`. |
| **Module** | `src/output/csv_writer.py` |
| **Expected behavior** | Python's `csv.DictWriter` with default `quoting=csv.QUOTE_MINIMAL` handles this. But verify that Excel opens the file without column misalignment. Use `csv.QUOTE_ALL` as a safer default. |

### EC-4.3 — UTF-8 encoding with BOM for Excel compatibility

| Attribute | Detail |
|-----------|--------|
| **Trigger** | Excel on Windows defaults to local encoding (e.g. Windows-1252) when opening CSV. Unicode characters (emoji, accented text) in reviews will render as garbage. |
| **Module** | `src/output/csv_writer.py` |
| **Expected behavior** | Write with `encoding="utf-8-sig"` (UTF-8 with BOM). This forces Excel to use UTF-8. |
| **Example** | A review: `"Can't find my photo from Zürich 🏔️"` — must render correctly in Excel. |

### EC-4.4 — `evidence_quote` contains pipe character `|`

| Attribute | Detail |
|-----------|--------|
| **Trigger** | If a raw review text contains the pipe `|` character and the LLM extracts it as part of `evidence_quote`, it could conflict with the `failure_point` pipe-delimiter in CSV. |
| **Module** | `src/output/csv_writer.py` |
| **Expected behavior** | No conflict — `failure_point` is serialized in its own column, and `evidence_quote` is in a separate column. Standard CSV quoting handles pipe characters inside field values. No special handling needed. |

### EC-4.5 — Zero tagged items after classification

| Attribute | Detail |
|-----------|--------|
| **Trigger** | All items are classified as `is_relevant: "no"` (extremely unlikely but theoretically possible). |
| **Module** | `src/output/csv_writer.py`, `src/output/stats.py` |
| **Expected behavior** | Write a CSV with only the header row. `summary_stats.json` shows `total_tagged: 0`. Log a `CRITICAL` error — this means the prompt, data, or model is fundamentally broken. |

### EC-4.6 — `summary_stats.json` — `by_failure_point` sums exceed `total_tagged`

| Attribute | Detail |
|-----------|--------|
| **Trigger** | `failure_point` is multi-label. An item with `["expression", "refinement"]` contributes to both counts. |
| **Module** | `src/output/stats.py` |
| **Expected behavior** | This is **correct and expected**. The stats file or a comment in it should note: `"Note: failure_point is multi-label; counts sum to more than total_tagged."` |

### EC-4.7 — Validation sample requested but dataset has <75 rows

| Attribute | Detail |
|-----------|--------|
| **Trigger** | `tagged_dataset.csv` has only 40 relevant rows — fewer than the configured `sample_size: 75`. |
| **Module** | `src/validation/sampler.py` |
| **Expected behavior** | Sample **all available rows** instead of 75. Log: `"Only 40 tagged items available. Sampling all instead of 75."` Proceed — partial validation is better than none. |

---

## 5. Pipeline Orchestration Edge Cases

### EC-5.1 — Running `--stage classify` without prior `--stage filter`

| Attribute | Detail |
|-----------|--------|
| **Trigger** | User runs `python -m src.main --stage classify` but `data/filtered/filtered_items.json` does not exist. |
| **Module** | `src/main.py` |
| **Expected behavior** | Print clear error: `"ERROR: data/filtered/filtered_items.json not found. Run --stage filter first (or run the full pipeline)."` Exit with code 1. |

### EC-5.2 — Running `--stage collect` twice overwrites raw data

| Attribute | Detail |
|-----------|--------|
| **Trigger** | User runs collect twice — second run overwrites `data/raw/*.json` with fresh data. If the first run had better coverage, data is lost. |
| **Module** | `src/collectors/base.py` |
| **Expected behavior** | **Overwrite is the default behavior** (simple, matches the "re-runnable" requirement). To be safe, log the item count of the existing file before overwriting: `"Overwriting play_store_raw.json (was: 423 items, now: 450 items)"`. |

### EC-5.3 — Resume logic hash collision

| Attribute | Detail |
|-----------|--------|
| **Trigger** | Two different items produce the same SHA-256 hash (astronomically unlikely, but the hash is truncated to 16 hex chars = 64 bits). |
| **Module** | `src/classifier/tagger.py` |
| **Expected behavior** | Accept the negligible risk. With ~1000 items, collision probability is ~0.00000003%. If paranoid, use the full 64-char hash. |

### EC-5.4 — Keyboard interrupt (Ctrl+C) during classification

| Attribute | Detail |
|-----------|--------|
| **Trigger** | User presses Ctrl+C while the classifier is running through 1100 items. |
| **Module** | `src/main.py`, `src/classifier/tagger.py` |
| **Expected behavior** | Catch `KeyboardInterrupt`. Write all already-classified items to `tagged_dataset.csv` before exiting. This ensures the resume logic works on next run. Log: `"Interrupted. Saved 347/1102 items. Re-run to resume."` |

### EC-5.5 — Disk full during file write

| Attribute | Detail |
|-----------|--------|
| **Trigger** | `data/tagged_dataset.csv` write fails because disk is full. |
| **Module** | `src/output/csv_writer.py`, `src/utils/io.py` |
| **Expected behavior** | `IOError` / `OSError` propagates. Log the error. The in-memory data is lost, but raw and filtered files are still on disk — re-run `--stage classify` to regenerate. |

### EC-5.6 — Multiple full-pipeline runs produce non-deterministic results

| Attribute | Detail |
|-----------|--------|
| **Trigger** | Two full runs produce slightly different datasets because: (1) scrapers pull live data that changes over time; (2) Reddit/Play Store review order shifts. |
| **Module** | Entire pipeline |
| **Expected behavior** | **Expected.** Live scraping is inherently non-deterministic. The LLM classification itself IS deterministic (`temperature=0.0`). To reproduce exactly, re-use saved `data/raw/*.json` files from a previous run. |

---

## 6. Data Quality & Schema Edge Cases

### EC-6.1 — Review is relevant but about a different Google product

| Attribute | Detail |
|-----------|--------|
| **Trigger** | "I can't find files in Google Drive" — relevant to search/retrieval, but wrong product. Collected from Reddit keyword search for `"google photos search"`. |
| **Module** | `src/classifier/tagger.py` |
| **Expected behavior** | The LLM should mark `is_relevant: "no"` because the prompt specifies "Google Photos user review." If the LLM is uncertain, it may mark `is_relevant: "yes"` with `content_type: "document"` — this is an acceptable edge case caught in validation. |

### EC-6.2 — Review describes both a search issue AND an unrelated complaint

| Attribute | Detail |
|-----------|--------|
| **Trigger** | "This app keeps crashing AND I can never find my old screenshots when I search for them." Contains exclusion keyword "crashes" but also a valid search complaint. |
| **Module** | `src/filter/keyword_filter.py` |
| **Expected behavior** | **The item will be dropped** by the keyword filter (matches `"crashes"`). This is a known false positive of the conservative filter. The PRD accepts this trade-off — the LLM is the real arbiter, but this item never reaches it. |
| **Mitigation** | If filter stats show high drop rates, refine keywords to be more contextual. |

### EC-6.3 — Review text is very short (<10 words)

| Attribute | Detail |
|-----------|--------|
| **Trigger** | Play Store review: `"can't find my photos"` (5 words). |
| **Module** | `src/classifier/tagger.py` |
| **Expected behavior** | The LLM should still classify it. Most fields will be `"not_mentioned"` or brief. `evidence_quote` may be the entire review. This is valid — short reviews still carry signal. |

### EC-6.4 — Review text is a sarcastic or ironic complaint

| Attribute | Detail |
|-----------|--------|
| **Trigger** | "Great search feature! Only took me 3 hours to find a photo from last week. 10/10 would search again." (Sarcasm — actually a complaint.) |
| **Module** | `src/classifier/tagger.py` |
| **Expected behavior** | The LLM should detect sarcasm and classify this as `is_relevant: "yes"`, `outcome: "found"` (eventually found), `failure_point: ["expression"]` or similar. Sarcasm detection accuracy varies by model — document misclassifications in validation. |

### EC-6.5 — `date` field has inconsistent formats across sources

| Attribute | Detail |
|-----------|--------|
| **Trigger** | Play Store returns dates like `datetime(2026, 3, 15)`. Reddit uses Unix timestamps. Apple RSS uses ISO 8601 (`"2026-03-15T10:30:00-07:00"`). |
| **Module** | All collectors |
| **Expected behavior** | Each collector must normalize to `"YYYY-MM-DD"` string format. If the date is unparseable, set to `null`. Never pass raw timestamps or locale-specific strings (`"March 15, 2026"`) to the schema. |

### EC-6.6 — `rating` field is a string instead of a float

| Attribute | Detail |
|-----------|--------|
| **Trigger** | Apple RSS returns `im:rating.label` as `"4"` (string). Play Store returns `score` as a float `4.0`. |
| **Module** | `src/collectors/app_store.py`, `src/classifier/schema.py` |
| **Expected behavior** | Each collector must cast to `float`. The `RawItem` schema has `rating: Optional[float]`. A `"4"` string will fail Pydantic validation — cast before constructing the model. |

### EC-6.7 — Forum thread with hundreds of replies

| Attribute | Detail |
|-----------|--------|
| **Trigger** | A Google Community forum thread has 200+ replies. Collecting all as separate items inflates volume from a single discussion. |
| **Module** | `src/collectors/forum.py` |
| **Expected behavior** | Collect the **original post + first 3–5 replies only** (per the architecture doc). Each reply is a separate `RawItem`. Set `url` to the thread URL for all of them. |

---

## 7. Environment & Configuration Edge Cases

### EC-7.1 — Missing `.env` file or missing keys

| Attribute | Detail |
|-----------|--------|
| **Trigger** | User forgot to create `.env`, or it exists but is missing `GROQ_API_KEY`. |
| **Module** | `src/utils/io.py` (at config load time) |
| **Expected behavior** | Fail fast at startup with a clear message: `"ERROR: GROQ_API_KEY not found in .env. Copy .env.example to .env and fill in your credentials."` Do not proceed to any pipeline stage. |

### EC-7.2 — Invalid Groq API key

| Attribute | Detail |
|-----------|--------|
| **Trigger** | `GROQ_API_KEY` is set but the key is expired, revoked, or malformed. |
| **Module** | `src/classifier/groq_client.py` |
| **Expected behavior** | First API call returns 401 Unauthorized. Catch this, log: `"ERROR: Groq API key is invalid. Verify at console.groq.com."`, and exit. Do NOT retry 3 times on auth errors — they're not transient. |

### EC-7.3 — `settings.yaml` has invalid model name

| Attribute | Detail |
|-----------|--------|
| **Trigger** | User sets `model: "llama-3-70b"` (wrong model ID). Groq API returns 404 or a model-not-found error. |
| **Module** | `src/classifier/groq_client.py` |
| **Expected behavior** | First API call fails with model-not-found. Log: `"ERROR: Model 'llama-3-70b' not found on Groq. Check available models at console.groq.com/docs/models."` Exit. |

### EC-7.4 — `settings.yaml` is malformed YAML

| Attribute | Detail |
|-----------|--------|
| **Trigger** | Indentation error, missing colon, or tabs instead of spaces in `settings.yaml`. |
| **Module** | `src/utils/io.py` |
| **Expected behavior** | `yaml.safe_load()` raises `yaml.YAMLError`. Catch and print: `"ERROR: config/settings.yaml is not valid YAML. Check for indentation errors."` Exit with code 1. |

### EC-7.5 — `classification.txt` prompt file is missing or empty

| Attribute | Detail |
|-----------|--------|
| **Trigger** | `config/prompts/classification.txt` doesn't exist or is 0 bytes. |
| **Module** | `src/utils/io.py`, `src/classifier/tagger.py` |
| **Expected behavior** | Fail fast: `"ERROR: Prompt file not found at config/prompts/classification.txt."` The system prompt is critical — running without it produces garbage. |

### EC-7.6 — Reddit anti-bot or login wall blocks browser agent

| Attribute | Detail |
|-----------|--------|
| **Trigger** | Reddit detects automated browsing and serves a login wall, CAPTCHA, or "something went wrong" page. |
| **Module** | `src/collectors/reddit.py` |
| **Expected behavior** | Log: `"WARNING: Reddit blocked browser agent. Returning partial results."` Return whatever items were collected before the block. Operator can re-run with different timing or manually supplement `data/raw/reddit_raw.json`. |

### EC-7.7 — Running on Python <3.10

| Attribute | Detail |
|-----------|--------|
| **Trigger** | The code uses `match` statements or `type1 | type2` union syntax (Python 3.10+). Or Pydantic v2 requires Python ≥3.8 but some features need 3.10+. |
| **Module** | All |
| **Expected behavior** | Add a version check in `src/main.py`: `if sys.version_info < (3, 10): sys.exit("Python 3.10+ required.")` |

---

## Summary Statistics

| Category | Count |
|----------|-------|
| Collection edge cases | 13 |
| Filter edge cases | 5 |
| Classification edge cases | 13 |
| Output edge cases | 7 |
| Orchestration edge cases | 6 |
| Data quality edge cases | 7 |
| Environment edge cases | 7 |
| **Total** | **58** |

---

> [!TIP]
> Use this document as a **test matrix** during implementation. Each `EC-X.Y`
> identifier can be referenced in code comments, commit messages, or test names
> (e.g. `test_ec_1_9_single_entry_dict()`).
