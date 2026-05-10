# utils.py
from __future__ import annotations
import logging
import re

from playwright.async_api import Page
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from urllib.parse import urljoin, urlparse

from llm.prompt import ELEMENT_EXTRACTOR_JS

# Helpers function for manual fileter
PRIVACY_KEYWORDS = (
    "privacy", "privacybeleid", "cookie", "gegevensbescherming"
)

TERMS_KEYWORDS = (
    "terms", "conditions", "voorwaarden",
    "gebruiksvoorwaarden", "servicevoorwaarden"
)

DISCLAIMER_KEYWORDS = (
    "disclaimer", "aansprakelijkheid", "vrijwaring"
)

ALL_GROUPS = [
    PRIVACY_KEYWORDS,
    TERMS_KEYWORDS,
    DISCLAIMER_KEYWORDS,
]

ARTICLE_KEYWORDS = (
    # English
    "article", "blog", "post", "story", "insight",
    "publication", "write-up",

    # Dutch
    "artikel", "blog", "bericht", "verhaal", "inzichten",
    "publicatie"
)

NEWS_KEYWORDS = (
    # Dutch
    "nieuws", "laatste", "update", "pers", "aankondiging",
    "kop", "breaking"
    
    # English
    "news", "latest", "update", "press", "announcement",
    "headline", "breaking",
)

PROJECT_KEYWORDS = (
    # English
    "project", "case study", "portfolio", "work", "client work",
    "implementation", "deployment",

    # Dutch
    "project", "case", "portfolio", "werk", "klantcase",
    "implementatie", "realisatie"
)

DYNAMIC_CLASS = re.compile(
        r'^(css|sc|styled|emotion|jsx|svelte|ng|v)-'  # CSS-in-JS prefixes
        r'|^[a-z]{1,3}-?[0-9a-f]{5,}$'               # hashed names
        r'|^\d',                                        # starts with digit — INVALID CSS
        re.I
    )

IGNORE_CLASSES = {
    # --- existing classes --- 
    "flex", "grid", "block", "inline", "inline-block", "inline-flex", "hidden",
    "items-center", "items-start", "items-end",
    "justify-center", "justify-between", "justify-start", "justify-end",
    # tailwind sizing that starts with numbers
    "2xl", "3xl", "4xl", "1/2", "1/3", "2/3",
    # ... rest of your ignore list
}

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


async def extract_links(result, validate_keywords: list, footer_link=False):
    texts, urls = [], []
    seen = set()

    keyword_used = set()

    internal = result.get("internal_links", [])
    external = result.get("external_links", [])

    all_links = internal + external

    def score_link(text, href):
        text = (text or "").lower()
        href = (href or "").lower()

        return sum(
            2 if k in text else 1 if k in href else 0
            for k in validate_keywords
        )

    # rank best matches first
    all_links.sort(
        key=lambda l: score_link(l.get("text"), l.get("href")),
        reverse=True
    )

    for link in all_links:
        try:
            text = (link.get("text") or "").strip()
            href = (link.get("href") or "").strip().lower()

            # validate the link
            if not is_valid_link(href) or href in seen:
                continue

            # add on seen to not override same link
            seen.add(href)

            # match the link with keyword
            matched_keyword = next(
                (k for k in validate_keywords if (k in href or k in text) 
                 and k not in keyword_used),
                None,
            )
            if not matched_keyword: continue
            
            # no more than 2 links
            if not footer_link:
                if len(urls) >= 2: break
                
                # take links with 
                path_parts = [p for p in urlparse(href).path.rstrip("/").split("/") if p]
                if path_parts and matched_keyword in path_parts[-1] \
                and len(path_parts) == 1:
                    continue

            keyword_used.add(matched_keyword)
            texts.append(text)
            urls.append(href)


        except Exception as e:
            logging.warning(f"Skipping link: {e}")

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


async def get_elements(page: Page):
        """Evaluate Js function on page to extract elements and its attributes"""
        elements = await page.evaluate(ELEMENT_EXTRACTOR_JS)
        return elements


def get_meaningful_classes(el: dict) -> list:
    raw = el.get("class") or ""
    return [
        c for c in raw.strip().split()
        if c
        and c not in IGNORE_CLASSES
        and not DYNAMIC_CLASS.match(c)
        and c[0].isalpha()          # must start with a letter — hard CSS rule
        and c.replace("-", "").replace("_", "").isalnum()  # only safe chars
    ]


# def build_selector(el: dict) -> str:
#     tag = el["tag"]

#     if el["id"]:
#         return f"#{el['id']}"

#     classes = get_meaningful_classes(el)
#     if classes:
#         return f"{tag}.{classes[0]}"   # first meaningful class only

#     return tag

import re

def escape_css_class(cls: str) -> str:
    # Escape every non-alphanumeric character
    return re.sub(r'([^a-zA-Z0-9_-])', r'\\\1', cls)

def build_selector(el: dict) -> str:
    tag = el["tag"]

    if el.get("id"):
        return f"#{escape_css_class(el['id'])}"

    class_attr = el.get("class", "")

    if class_attr:
        classes = class_attr.split()

        escaped = [escape_css_class(c) for c in classes]

        return f"{tag}." + ".".join(escaped)

    return tag


def is_specific(selector: str, el: dict) -> bool:
    tag = el["tag"]

    # keep if has meaningful classes
    if get_meaningful_classes(el):
        return True
    
    # always keep semantic tags regardless
    if tag in {"header", "footer", "nav", "section", "div"}:
        return True

    # always keep role-based elements
    if el.get("role") in {"banner", "contentinfo", "navigation", "main"}:
        return True
    
    # keep if id
    if selector.startswith("#") or "." in selector:
        return True
    
    # drop bare generic tags like "div", "section"
    return False


def is_header_like(el: dict):
    tag = el.get("tag", "").lower()
    cls = (el.get("class") or "").lower()
    eid = (el.get("id") or "").lower()
    role = (el.get("role") or "").lower()
    text = (el.get("text") or "").lower()
    KEYWORDS = {"header", "menu", "top", "nav"}
    return (
        tag in {"header", "nav"} or role in {"banner", "navigation"} or
        "header" in cls.split() or "nav" in cls.split() or
        any(k in eid.lower() for k in KEYWORDS) or \
        any(k in cls.lower() for k in KEYWORDS) or "navbar" in cls or
        "logo" in cls or "menu" in text[:100] 
    )


def is_footer_like(el: dict):
    tag = el.get("tag", "").lower()
    cls = (el.get("class") or "").lower()
    eid = (el.get("id") or "").lower()
    text = (el.get("text") or "").lower()

    return (
        tag == "footer" or "footer" in cls.split() or
        "footer" in eid or "copyright" in cls or
        "terms" in cls or "privacy" in cls or
        "©" in text or "all rights reserved" in text
    )

def dedupe_lines(text: str) -> str:
    seen,out = set(),[]

    for line in text.splitlines():
        line = line.strip()

        if not line: continue

        if line in seen: continue
        seen.add(line)
        out.append(line)

    return "\n".join(out)