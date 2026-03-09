# DeSoto County News Auto

Automated RSS feed monitoring, AI-powered article rewriting, and WordPress publishing for [DeSotoCountyNews.com](https://desotocountynews.com).

## Features

- **RSS Feed Monitoring**: Parse RSS/Atom feeds with robust error handling
- **AI Rewriting**: Convert feed content to AP-style news using GPT-5 mini with GPT-4.1 nano fallback
- **Smart Deduplication**: SQLite-based tracking ensures no duplicate posts
- **Image Handling**: 
  - Extract images from RSS (media:content, enclosures, HTML)
  - Fallback to Pexels/Unsplash for stock photos
  - Proper attribution in alt text
- **WordPress Publishing**: Full REST API integration with categories and tags
- **Quality Guardrails**: Skips low-information or placeholder feed entries
- **Scheduling**: GitHub Actions (every 15 min) or VPS cron/systemd

## Quick Start

### 1. Clone and Install

```bash
git clone https://github.com/wallyrebel/desotocountynews.git
cd desotocountynews

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
pip install -e .
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your API keys
```

**Required variables:**
- `OPENAI_API_KEY` - Your OpenAI API key
- `WORDPRESS_BASE_URL` - Your WordPress site URL
- `WORDPRESS_USERNAME` - WordPress username
- `WORDPRESS_APP_PASSWORD` - WordPress Application Password

### 3. Run

```bash
# Full run
python -m rss_to_wp run --config feeds.yaml

# Dry run (no publishing)
python -m rss_to_wp run --config feeds.yaml --dry-run

# Check status
python -m rss_to_wp status
```

## Feed Sources

- **13 DeSoto County local feeds** via FetchRSS
- **Mississippi Today** for statewide Mississippi news

## GitHub Actions

The workflow runs every 15 minutes automatically. Add your secrets in **Settings > Secrets and variables > Actions**:

| Secret | Required | Description |
|--------|----------|-------------|
| `OPENAI_API_KEY` | ✅ | OpenAI API key |
| `WORDPRESS_BASE_URL` | ✅ | `https://desotocountynews.com` |
| `WORDPRESS_USERNAME` | ✅ | WordPress username |
| `WORDPRESS_APP_PASSWORD` | ✅ | Application password |
| `PEXELS_API_KEY` | ❌ | Pexels API key |
| `TIMEZONE` | ❌ | `America/Chicago` |

## Project Structure

```
.
├── src/rss_to_wp/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py              # CLI commands
│   ├── config.py           # Configuration models
│   ├── feeds/              # RSS parsing & filtering
│   ├── images/             # Image extraction & fallbacks
│   ├── rewriter/           # OpenAI AP-style rewriting
│   ├── storage/            # SQLite deduplication
│   ├── utils/              # Logging & HTTP utilities
│   └── wordpress/          # WP REST API client
├── data/                   # Runtime data (gitignored)
│   └── processed.db
├── .github/workflows/
│   └── rss_to_wp.yml
├── feeds.yaml
├── .env.example
├── pyproject.toml
├── requirements.txt
└── README.md
```

## License

MIT License
