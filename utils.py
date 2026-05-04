# utils.py

from playwright.async_api import Page
import logging

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


#TODO better link filter
async def extract_links(page: Page, selector: str, validate_keywords: list):
    """Extracts links based on keyword matching from page's css selector"""
    texts, urls = [], []
    seen = set()
    links = page.locator(f"{selector} a")

    # go through ith link
    for i in range(await links.count()):
        try:
            text = (await links.nth(i).inner_text()).strip().lower()
            href = (await links.nth(i).get_attribute("href") or "").strip().lower()

            # validate the link
            if not is_valid_link(href) or href in seen:
                continue

            # add on seen to not override same link
            seen.add(href)

            # match the link with keyword
            matched_keyword = next((k for k in validate_keywords if k in href or k in text), None)
            if not matched_keyword:
                continue
            
            # if the body link must be full.
            if selector == "body":
                path_parts = [p for p in urlparse(href).path.rstrip("/").split("/") if p]

                # take links with more than one /
                if path_parts and matched_keyword in path_parts[-1] and len(path_parts) == 1:
                    continue
                return [text], [href]

            texts.append(text)
            urls.append(href)

        except Exception as e:
            logging.warning(f"Skipping link {i}: {e}")

    return texts, urls