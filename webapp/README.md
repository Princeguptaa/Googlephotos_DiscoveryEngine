# Google Photos Discovery Engine — Web App

A Flask web application that classifies Google Photos user reviews/posts
through the same LLM pipeline used in the main Discovery Model.

## Live Demo

🔗 **[Try it on Render](https://googlephotos-discoveryengine.onrender.com)**

## What It Does

Paste any Google Photos review or post and the engine will classify:
- **is_relevant** — Is this genuinely about retrieving a photo from memory?
- **content_type** — photo / screenshot / document / video
- **retrieval_scenario** — What they were trying to find
- **failure_point** — Where in the retrieval process things broke down
- **scenario_type** — vague_memory vs general_search_quality
- **evidence_quote** — Verbatim phrase supporting the classification

## Stack

| Layer     | Technology                    |
|-----------|-------------------------------|
| Backend   | Flask + Gunicorn              |
| LLM       | Groq (openai/gpt-oss-20b)    |
| Frontend  | Vanilla HTML/CSS/JS           |
| Hosting   | Render (Free Web Service)     |

## Local Development

```bash
cd webapp
pip install -r requirements.txt

# Create a .env file with your Groq API key
echo "GROQ_API_KEY=gsk_your_key_here" > .env

python app.py
# → http://localhost:5000
```

## Deployment (Render)

1. Push to GitHub
2. On [Render](https://render.com), create a **New Web Service**
3. Connect the repo, set:
   - **Root Directory:** `webapp`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
4. Add environment variable: `GROQ_API_KEY` = your key
5. Deploy ✅

## Environment Variables

| Variable       | Required | Description                              |
|----------------|----------|------------------------------------------|
| `GROQ_API_KEY` | ✅       | Groq API key for LLM classification      |
| `GROQ_MODEL`   | ❌       | Model override (default: openai/gpt-oss-20b) |
