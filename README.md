# SalesSwarm 🐝

AI-powered B2B sales outreach automation. Enter a target company — SalesSwarm researches, qualifies, finds contacts, and generates personalized cold emails, WhatsApp messages, LinkedIn DMs, and follow-ups.

## How It Works

```
Target URL → Researcher → Fit Analyzer → Qualifier
                                            │
                              ┌─────────────┴─────────────┐
                              │                           │
                         [Qualified]                [Not Qualified]
                              │                           │
                       Contact Finder              Recommender
                              │                           │
                       Hook Finder                     Finalize
                              │
                       Copywriter
                              │
                        Finalize → Response
```

### Agents

| Agent | What it does |
|-------|-------------|
| **Researcher** | Scrapes homepage, about, pricing pages via Jina AI; extracts company info |
| **Fit Analyzer** | Scores fit (1–10), identifies pain points, objections, best angle |
| **Qualifier** | Applies rule-based checks (company size vs ICP), sets `qualified` flag |
| **Contact Finder** | Discovers company LinkedIn, key person (CEO/HR), their LinkedIn, email, WhatsApp |
| **Recommender** | Suggests alternative target companies when the current one doesn't fit |
| **Hook Finder** | Finds a personalized hook from company signals (job postings, news, etc.) |
| **Copywriter** | Writes cold email, WhatsApp message, LinkedIn DM, follow-up email |

## Tech Stack

- **Backend**: Python, FastAPI, LangGraph, Groq (Llama 3.1), Jina AI
- **Frontend**: Vanilla HTML/CSS/JS with Tailwind CSS CDN
- **Async**: asyncio, httpx, uvicorn

## Quick Start

```bash
# Clone and enter
git clone <repo-url>
cd salesswarm

# Create venv and install deps
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your API keys (GROQ_API_KEY, JINA_API_KEY)

# Run
uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000` in your browser.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Yes | — | Groq API key for LLM inference |
| `JINA_API_KEY` | Yes | — | Jina AI API key for web scraping and search |
| `GROQ_MODEL` | No | `llama-3.1-8b-instant` | Groq model identifier |

## API

### `POST /swarm`

```json
{
  "target_url": "https://example.com",
  "founder_product": "B2B sales automation platform",
  "founder_icp": "B2B SaaS companies with 10-200 employees"
}
```

Returns a full outreach kit with contact info, hooks, email drafts, WhatsApp message, LinkedIn DM, and follow-up.

### `GET /health`

Returns `{"status": "SalesSwarm is live 🐝"}`

## Deployment

### Vercel (Pro plan required)

1. Push to GitHub
2. Import repo on Vercel
3. Set environment variables in Vercel dashboard
4. Ensure **Max Duration** is set to 60s in project settings
5. Deploy — zero-config for Python

See `vercel.json` for configuration.
