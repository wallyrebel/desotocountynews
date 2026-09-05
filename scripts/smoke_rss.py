"""Non-publishing smoke test against real RSS feeds and the configured models."""
import json
from pathlib import Path
from rss_to_wp.config import get_app_settings, load_feeds_config
from rss_to_wp.feeds import parse_feed, get_entry_content, get_entry_title, get_entry_link
from rss_to_wp.feeds.filter import parse_entry_date
from rss_to_wp.rewriter.grounded import GroundedRewriter

settings = get_app_settings()
writer = GroundedRewriter(settings.openai_api_key, model=settings.openai_model,
    extraction_model=settings.openai_extraction_model,
    target_min_words=settings.article_target_min_words)
results = []
attempts = 0
for config in load_feeds_config('feeds.yaml').feeds:
    if config.republish:
        continue
    feed = parse_feed(config.url)
    if not feed or not feed.entries:
        continue
    for entry in feed.entries[:2]:
        attempts += 1
        result = writer.rewrite(get_entry_content(entry), get_entry_title(entry),
            source_name=config.name, source_url=get_entry_link(entry) or '',
            published_at=str(parse_entry_date(entry) or ''))
        if result and result.get('_audit'):
            results.append(result)
            print('SMOKE_ARTICLE ' + json.dumps(result, ensure_ascii=False), flush=True)
        if len(results) >= 3 or attempts >= 8:
            break
    if len(results) >= 3 or attempts >= 8:
        break
Path('data').mkdir(exist_ok=True)
Path('data/smoke-results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
assert len(results) >= 2, f'Only {len(results)} source-verified articles from {attempts} attempts'
print(f'LIVE_SMOKE_PASSED: {len(results)} articles; no WordPress writes')
