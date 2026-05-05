# utils.py

import logging

from playwright.async_api import Page
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

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


async def extract_links(page: Page, selector: str, validate_keywords: list,use_crawl4ai=False):
    """Extracts links based on keyword matching from page's css selector"""
    texts, urls = [], []
    seen = set()
    keyword_used = set()

    # links_html = await page.locator(selector).inner_html()
    # Merge innerHTML from ALL matched elements — handles duplicate selectors
    links_html = await page.locator(selector).evaluate_all(
        "els => els.map(e => e.innerHTML).join('')"
    )

    # now scrape using crawl4ai
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=f"raw:{links_html}",
            config=CrawlerRunConfig(js_code=None, wait_for=None),
        )

    # TODO might need external links for some webpage, terms and privacy  
    for link in result.links["internal"]:
        try:
            text = link["text"].strip().lower()
            href = (link.get("href") or "").strip().lower()

            # validate the link
            if not is_valid_link(href) or href in seen:
                continue

            # add on seen to not override same link
            seen.add(href)

            # match the link with keyword
            matched_keyword = next(
                (k for k in validate_keywords if (k in href or k in text) and k not in keyword_used),
                None,
            )
            if not matched_keyword: continue
            
            # no more than 2 links
            if selector == "body":
                if len(urls) >= 2: break
                
                # take links with 
                path_parts = [p for p in urlparse(href).path.rstrip("/").split("/") if p]
                if path_parts and matched_keyword in path_parts[-1] and len(path_parts) == 1:
                    continue

            keyword_used.add(matched_keyword)
            texts.append(text)
            urls.append(href)

        except Exception as e:
            logging.warning(f"Skipping link {text}: {e}")

    return texts, urls


def clean_cookies(raw_cookies):
    """Cleaned json cookies"""
    cleaned = []

    for c in raw_cookies:
        cookie = {
            "name": c["name"],"value": c["value"],"domain": c["domain"],
            "path": c.get("path", "/"),"secure": c.get("secure", False),
            "httpOnly": c.get("httpOnly", False),
        }

        # Fix sameSite
        same_site = c.get("sameSite")
        if same_site in ["Strict", "Lax", "None"]:
            cookie["sameSite"] = same_site
        else:
            cookie["sameSite"] = "Lax"   # default fallback

        # Expiry (Playwright uses "expires", not "expirationDate")
        if "expirationDate" in c:
            cookie["expires"] = c["expirationDate"]

        cleaned.append(cookie)

    return cleaned