# AI-Powered Discovery Engine — Google Photos Retrieval Research

A batch pipeline that scrapes public user feedback about Google Photos
search/retrieval from 4 sources, filters and classifies each item using
Groq's LLM API, and produces a structured dataset for analysis.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up credentials
cp .env.example .env
# Edit .env with your Groq API key

# 3. Run the full pipeline
python -m src.main
```

## Pipeline Stages

| Stage | Description | Output |
|-------|-------------|--------|
| **Collect** | Scrape reviews from Play Store, Reddit, App Store, Google Photos forum | `data/raw/*_raw.json` |
| **Filter** | Remove obviously irrelevant items via keyword exclusion | `data/filtered/filtered_items.json` |
| **Classify** | Tag each item using Groq LLM into structured schema | `data/tagged_dataset.csv` |
| **Output** | Aggregate stats + validation sample | `data/summary_stats.json`, `data/validation_sample.csv` |

## Run Individual Stages

```bash
python -m src.main --stage collect
python -m src.main --stage filter
python -m src.main --stage classify   # Supports resume from partial progress
python -m src.main --stage output
python -m src.main --stage validate
```

## Configuration

Edit `config/settings.yaml` to change:
- Collection target volumes per source
- Groq model ID (e.g. swap `openai/gpt-oss-120b` → `meta-llama/llama-4-scout-17b`)
- Filter exclusion keywords
- Validation sample size

## Credentials Needed

- **Groq API:** API Key → [console.groq.com](https://console.groq.com)
