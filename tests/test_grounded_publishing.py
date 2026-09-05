from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from PIL import Image

from rss_to_wp import cli
from rss_to_wp.config import FeedConfig
from rss_to_wp.feeds.parser import get_entry_content
from rss_to_wp.images.brand import create_brand_image
from rss_to_wp.rewriter.grounded import (
    Article,
    Extraction,
    GroundedRewriter,
    Passage,
    Verification,
)
from rss_to_wp.wordpress.client import WordPressClient

SOURCE = "Southaven police will host a public meeting at City Hall on Sept. 10 at 6 p.m. Admission is free."


def article(text=SOURCE):
    passage = Passage(text=text, evidence_ids=[0])
    return Article(
        headline=Passage(text="Southaven police announce public meeting", evidence_ids=[0]),
        excerpt=passage,
        paragraphs=[passage],
    )


def writer(*responses):
    instance = GroundedRewriter.__new__(GroundedRewriter)
    instance.model = instance.extraction_model = "gpt-5.6-luna"
    instance.target_min_words = 150
    instance._structured = Mock(side_effect=responses)
    return instance


def extraction(evidence=SOURCE):
    return Extraction(publishable=True, reason="Specific public notice", evidence=[evidence])


def test_short_source_can_publish_without_padding():
    w = writer(extraction(), article(), Verification(supported=True, issues=[]))
    result = w.rewrite(SOURCE, "Meeting", source_name="Southaven Police Department")
    assert result and len(result["body"].split()) < 150
    assert result["_audit"]["rss_text"] == SOURCE
    assert w._structured.call_count == 3
    assert "ONLY the supplied evidence" in w._structured.call_args_list[1].args[2]


def test_fabricated_extraction_is_rejected_before_writing():
    w = writer(extraction("Three people were arrested."))
    assert w.rewrite(SOURCE, "Meeting") is None
    assert w._structured.call_count == 1


def test_unsupported_article_is_revised_against_feed():
    w = writer(
        extraction(),
        article("The mayor will attend."),
        Verification(supported=False, issues=["Mayor attendance is unsupported"]),
        article(),
        Verification(supported=True, issues=[]),
    )
    assert w.rewrite(SOURCE, "Meeting")
    assert w._structured.call_count == 5


def test_persistent_unsupported_claims_never_publish():
    failed = Verification(supported=False, issues=["Unsupported mayor attendance"])
    w = writer(
        extraction(),
        article("The mayor will attend."),
        failed,
        article("The mayor will attend."),
        failed,
    )
    assert w.rewrite(SOURCE, "Meeting") is None


def test_invalid_evidence_reference_rejected():
    a = article()
    a.headline.evidence_ids = [99]
    w = writer(extraction(), a)
    assert w.rewrite(SOURCE, "Meeting") is None


def test_no_news_facts_are_skipped():
    w = writer(Extraction(publishable=False, reason="Greeting only", evidence=[]))
    assert w.rewrite("Happy Friday!", "Hello")["_status"] == "skipped"


def test_long_source_is_not_silently_truncated():
    w = writer(extraction(), article(), Verification(supported=True, issues=[]))
    source = SOURCE + " Additional source text." * 600
    assert w.rewrite(source, "Meeting")
    assert w._structured.call_args_list[0].args[3]["rss_text"] == source


def test_html_is_escaped_in_output():
    text = "The sign reads <script>alert(1)</script>."
    w = writer(extraction(), article(text), Verification(supported=True, issues=[]))
    assert "<script>" not in w.rewrite(SOURCE, "Meeting")["body"]


def test_empty_content_uses_summary():
    assert get_entry_content({"content": [{"value": ""}], "summary": SOURCE}) == SOURCE


def test_branded_fallback_is_valid_featured_image():
    data, filename, mime = create_brand_image()
    image = Image.open(BytesIO(data))
    assert image.size == (1200, 630)
    assert filename.endswith(".png") and mime == "image/png"


@pytest.fixture
def publishing(monkeypatch):
    monkeypatch.setattr(cli, "find_rss_image", lambda *a, **kw: None)
    wp = Mock()
    wp.upload_media.return_value = 10
    wp.get_or_create_category.return_value = 20
    wp.get_or_create_tags.return_value = [30]
    wp.create_post.return_value = {"id": 40, "status": "publish", "link": "https://example.com/40"}
    rewriter = Mock()
    rewriter.rewrite.return_value = {"headline": "Public meeting", "body": f"<p>{SOURCE}</p>"}
    config = FeedConfig(name="Southaven Police Department", url="https://example.com/rss")
    entry = {
        "title": "Meeting",
        "summary": SOURCE,
        "link": "https://example.com/source",
        "published": "2026-09-05T12:00:00Z",
    }

    def run():
        return cli.process_entry(entry, config, SimpleNamespace(), rewriter, wp, False, Mock())

    return SimpleNamespace(run=run, wp=wp, rewriter=rewriter)


def test_short_story_publishes_with_required_metadata(publishing):
    assert publishing.run()["status"] == "publish"
    args = publishing.wp.create_post.call_args.kwargs
    assert args["featured_media_id"] == 10
    assert args["category_id"] == 20 and args["tag_ids"] == [30]
    assert args["status"] == "publish"
    assert (
        publishing.rewriter.rewrite.call_args.kwargs["source_name"] == "Southaven Police Department"
    )


@pytest.mark.parametrize("method", ["upload_media", "get_or_create_category", "get_or_create_tags"])
def test_missing_metadata_prevents_incomplete_post(publishing, method):
    getattr(publishing.wp, method).return_value = None
    assert publishing.run() is None
    publishing.wp.create_post.assert_not_called()


def test_wordpress_layer_also_requires_metadata():
    wp = WordPressClient("https://example.com", "user", "test")
    wp.session = Mock()
    assert wp.create_post("Headline", "<p>Body</p>") is None
    wp.session.post.assert_not_called()


def test_wordpress_duplicate_lookup_failure_defers_publication():
    wp = WordPressClient("https://example.com", "user", "test")
    wp.session = Mock()
    wp.session.get.side_effect = RuntimeError("unavailable")
    with pytest.raises(RuntimeError, match="Cannot verify"):
        wp.create_post(
            "Headline",
            "Body",
            category_id=1,
            tag_ids=[2],
            featured_media_id=3,
            source_url="https://example.com/source",
        )
    wp.session.post.assert_not_called()


def test_existing_wordpress_post_is_reconciled_without_new_post():
    wp = WordPressClient("https://example.com", "user", "test")
    wp.session = Mock()
    wp.session.get.return_value.json.return_value = [
        {"id": 12, "content": {"rendered": "Source: https://example.com/source"}}
    ]
    result = wp.create_post(
        "Headline",
        "Body",
        category_id=1,
        tag_ids=[2],
        featured_media_id=3,
        source_url="https://example.com/source",
    )
    assert result["_status"] == "already_published" and result["id"] == 12
    wp.session.post.assert_not_called()


def test_source_audit_is_saved_with_post(tmp_path):
    import json
    import sqlite3

    from rss_to_wp.storage import DedupeStore

    store = DedupeStore(tmp_path / "history.db")
    store.mark_processed(
        "key",
        "feed",
        "title",
        "source",
        wp_post_id=1,
        audit={"rss_text": SOURCE, "verification": {"supported": True}},
    )
    with sqlite3.connect(store.db_path) as conn:
        audit = json.loads(conn.execute("SELECT audit_json FROM article_audits").fetchone()[0])
    assert audit["rss_text"] == SOURCE
