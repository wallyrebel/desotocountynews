"""Utilities for republishing CC BY-ND licensed articles."""

from __future__ import annotations

import re
from typing import Any, Optional

from bs4 import BeautifulSoup

from rss_to_wp.utils import get_logger

logger = get_logger("republish")


def get_entry_author(entry: dict[str, Any]) -> str:
    """Extract author name from an RSS entry.

    Args:
        entry: Parsed RSS entry dictionary.

    Returns:
        Author name string, or empty string if not found.
    """
    # feedparser stores author in 'author' field
    author = entry.get("author", "")
    if author:
        return author.strip()

    # Some feeds use 'authors' list
    authors = entry.get("authors", [])
    if authors and isinstance(authors, list):
        names = [a.get("name", "") for a in authors if a.get("name")]
        if names:
            return ", ".join(names)

    # Try dc:creator
    creator = entry.get("dc_creator", "")
    if creator:
        return creator.strip()

    return ""


def build_republish_body(
    content: str,
    author: str,
    original_url: str,
    source_name: str = "Mississippi Today",
    source_url: str = "https://mississippitoday.org",
) -> str:
    """Wrap article content with byline header and attribution footer.

    The byline and attribution are placed at the TOP of the article
    so readers immediately see the original author and source.

    Args:
        content: Original article HTML content from RSS.
        author: Author name for the byline.
        original_url: URL of the original article.
        source_name: Display name of the source publication.
        source_url: Homepage URL of the source publication.

    Returns:
        Complete HTML body with byline + content + attribution footer.
    """
    # Build the byline/attribution header
    byline_parts = []

    if author:
        byline_parts.append(f"By <strong>{_escape_html(author)}</strong>")

    byline_parts.append(
        f'Originally published by '
        f'<a href="{source_url}" target="_blank" rel="noopener">{source_name}</a>'
    )

    byline_header = (
        f'<p><em>{" | ".join(byline_parts)}</em></p>\n'
    )

    # Clean the RSS content — remove images (photos excluded from CC license)
    cleaned_content = _strip_images(content)

    # Build the footer attribution
    attribution_footer = (
        f'\n<hr>\n'
        f'<p style="font-size: 0.9em; color: #666;"><em>'
        f'This article was originally published by '
        f'<a href="{original_url}" target="_blank" rel="noopener">{source_name}</a> '
        f'and is republished here under a '
        f'<a href="https://creativecommons.org/licenses/by-nd/4.0/" target="_blank" rel="noopener">'
        f'Creative Commons license</a>.</em></p>'
    )

    return byline_header + cleaned_content + attribution_footer


def _strip_images(html: str) -> str:
    """Remove <img> tags from HTML since photos are excluded from CC license.

    Args:
        html: HTML content string.

    Returns:
        HTML with images removed.
    """
    try:
        soup = BeautifulSoup(html, "html.parser")

        # Remove all img tags
        for img in soup.find_all("img"):
            img.decompose()

        # Remove empty figure/figcaption wrappers left behind
        for figure in soup.find_all("figure"):
            if not figure.get_text(strip=True):
                figure.decompose()

        return str(soup)
    except Exception:
        # Fallback: regex removal
        return re.sub(r"<img[^>]*>", "", html)


def _escape_html(text: str) -> str:
    """Escape HTML special characters in plain text.

    Args:
        text: Plain text string.

    Returns:
        HTML-safe string.
    """
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
