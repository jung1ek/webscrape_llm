# utils.py

from urllib.parse import urljoin, urlparse
from config import ALL_GROUPS


def normalize_url(base_url: str, link: str) -> str:
    """Convert relative URLs to absolute."""
    if urlparse(link).scheme in ("http", "https"):
        return link
    return urljoin(base_url, link)


def is_valid_link(href: str) -> bool:
    """Filter out invalid links. like js, anchor links"""
    if not href:
        return False
    return not any(
        href.startswith(prefix)
        for prefix in ("javascript:", "mailto:", "tel:", "#")
    )


def matches_keywords(value: str) -> bool:
    """Check if string matches any keyword group."""
    return any(
        keyword in value
        for group in ALL_GROUPS
        for keyword in group
    )