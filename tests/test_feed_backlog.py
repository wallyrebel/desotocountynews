from types import SimpleNamespace
from unittest.mock import Mock

import pendulum
import pytest

from rss_to_wp import cli
from rss_to_wp.config import FeedConfig
from rss_to_wp.feeds import generate_entry_key
from rss_to_wp.feeds.filter import parse_entry_date
from rss_to_wp.storage import DedupeStore


@pytest.fixture
def runner(tmp_path, monkeypatch):
    store = DedupeStore(tmp_path / "processed.db")
    config = FeedConfig(
        name="Test",
        url="https://example.com/feed",
        max_per_run=3,
        default_category="DeSoto County News",
    )
    entries = [
        dict(
            id=str(i),
            title=f"Story {i}",
            link=f"https://example.com/{i}",
            published=pendulum.now("UTC").subtract(minutes=10 - i).isoformat(),
        )
        for i in range(7)
    ]
    monkeypatch.setattr(cli, "parse_feed", lambda _: SimpleNamespace(entries=entries))
    monkeypatch.setattr(cli.time, "sleep", lambda _: None)
    publish = Mock(
        side_effect=lambda **kw: {"id": int(kw["entry"]["id"]) + 1, "link": kw["entry"]["link"]}
    )
    monkeypatch.setattr(cli, "process_entry", publish)

    def run(dry_run=False, limits=None, counts=None):
        return cli.process_feed(
            config,
            SimpleNamespace(timezone="UTC"),
            store,
            Mock(),
            Mock(),
            dry_run,
            48,
            Mock(),
            limits or {},
            counts if counts is not None else {},
        )

    return SimpleNamespace(run=run, store=store, entries=entries, publish=publish, config=config)


def test_backlog_drains_across_runs_and_database_reopen(runner):
    assert [runner.run()[0] for _ in range(4)] == [3, 3, 1, 0]
    assert [c.kwargs["entry"]["id"] for c in runner.publish.call_args_list] == list("0123456")
    assert DedupeStore(runner.store.db_path).get_processed_count() == 7


def test_new_arrivals_do_not_starve_backlog(runner):
    assert runner.run()[0] == 3
    runner.entries.append(
        dict(
            id="8",
            title="New",
            link="https://example.com/8",
            published=pendulum.now("UTC").isoformat(),
        )
    )
    runner.publish.reset_mock()
    assert runner.run()[0] == 3
    assert [c.kwargs["entry"]["id"] for c in runner.publish.call_args_list] == list("345")


@pytest.mark.parametrize("failure", [None, RuntimeError("temporary failure")])
def test_failure_does_not_block_posts_and_is_retried(runner, failure):
    runner.publish.side_effect = [failure, {"id": 2}, {"id": 3}, {"id": 4}]
    assert runner.run()[0] == 3
    key = generate_entry_key(runner.entries[0], runner.config.url)
    assert not runner.store.is_processed(key)
    runner.publish.reset_mock(side_effect=True)
    runner.publish.return_value = {"id": 99}
    assert runner.run()[0] == 3
    assert runner.publish.call_args_list[0].kwargs["entry"]["id"] == "0"
    assert runner.store.is_processed(key)


def test_quality_skips_do_not_consume_post_slots(runner):
    runner.publish.side_effect = [{"_status": "skipped"}, {"id": 2}, {"id": 3}, {"id": 4}]
    assert runner.run() == (3, 1, 0)
    assert runner.store.get_processed_count() == 4


def test_duplicate_dry_run_does_not_write_state(runner):
    runner.entries.insert(1, runner.entries[0].copy())
    assert runner.run(dry_run=True) == (3, 1, 0)
    assert runner.store.get_processed_count() == 0
    assert runner.run()[0] == 3
    assert runner.store.get_processed_count() == 3


def test_daily_category_cap(runner):
    category = runner.config.default_category
    counts = {category: 1}
    assert runner.run(limits={category: 2}, counts=counts)[0] == 1
    assert counts[category] == 2
    assert runner.run(limits={category: 2}, counts=counts)[0] == 0


def test_invalid_and_expired_entries_excluded(runner):
    runner.entries[0]["published"] = pendulum.now("UTC").subtract(hours=49).isoformat()
    del runner.entries[1]["published"]
    del runner.entries[2]["link"]
    assert runner.run()[0] == 3
    assert [c.kwargs["entry"]["id"] for c in runner.publish.call_args_list] == list("345")


def test_feedparser_timestamp_is_utc():
    import time

    parsed = time.struct_time((2026, 9, 5, 12, 30, 0, 5, 248, 0))
    assert parse_entry_date({"published_parsed": parsed}) == pendulum.datetime(2026, 9, 5, 12, 30)
