# DeSoto County News Auto

Automated RSS feed monitoring, AI-powered article rewriting, and WordPress publishing for [DeSotoCountyNews.com](https://desotocountynews.com).

## Features

- **RSS Feed Monitoring**: Parse RSS/Atom feeds with robust error handling
- **AI Rewriting**: Extract exact RSS evidence, write with Luna, and check source support before publishing
- **Deduplication**: SQLite tracking plus WordPress source-URL reconciliation
- **Image Handling**: 
  - Extract images from RSS (media:content, enclosures, HTML)
  - Neutral branded featured graphic when a source image is unavailable
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

## Backlog handling

Each feed publishes up to `max_per_run` successful articles per run. Eligible
entries are processed oldest first. Duplicates, low-information entries, and
temporary failures do not consume posting slots. Seven eligible articles drain
over three runs: 3, 3, then 1. Failed entries can be retried on the next run.
Dry runs do not mark entries processed.

The existing 48-hour freshness window and daily category limits still apply.
An article must still appear in its RSS feed and have a valid date and link.
There is no durable article queue; expired or removed entries cannot be recovered
automatically. GitHub Actions serializes publishers and saves posting history
after failed runs. Cache eviction or a crash between publishing to WordPress and
recording success can still require reconciliation.

Run regression tests with `python -m pytest tests` after installing `.[dev]`.

## Feed Sources

- **14 local and regional feeds** via FetchRSS, including Southaven Police Department
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

## RSS-only editorial pipeline

Normal RSS stories use separate structured Luna calls for extraction, writing,
and source-support checking. Extraction quotes must match the RSS title/body
verbatim. Writing receives only those quotes and source metadata, with no web tools.
One revision is allowed for unsupported claims. Failed checks retry on a later run;
no unsupported article or draft is created. The soft body target is 150 words:
short factual briefs are allowed, and padding is forbidden.

Every new post requires an uploaded featured image, a category and at least one
tag. Use the RSS image when available; otherwise create a neutral DeSoto County
News graphic. Missing metadata blocks publication until a later retry. Posts are
explicitly published. Mississippi Today retains its original-text republish route.

Source text, evidence, passages, model IDs and the support verdict are stored in
SQLite article_audits with successful processing. A model check is not a guarantee:
it checks support in the feed, not external truth. Source corrections still need
reconciliation. Schedules remain every 15 minutes with up to three successful posts
per feed per run, subject to available feed content, the 48-hour window and daily
category caps. Actions uses Luna for extraction/writing and a 150-word soft target.
