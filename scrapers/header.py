# scrapers/header.py

from playwright.async_api import Page

from config import TOPBAR_SELECTORS, HEADER_FALLBACK_SELECTORS, PAYWALL_KEYWORDS
from utils import extract_links


async def scrape_header(page: Page) -> dict:
    """Extract header and authentication-related links."""
    selectors_used = []

    topbar_selector = None
    header_selector = None
    
    top_bar = None
    
    # top bar link's href and text
    topbar_text = []
    topbar_link = []

    # Topbar detection
    for selector in TOPBAR_SELECTORS:
        if await page.locator(selector).count():
            top_bar = await page.locator(selector).all_inner_texts()
            topbar_selector = selector
            selectors_used.append(selector)
            break
        
    header = None

    # header link's text and href
    header_text = []
    header_link = []

    # Header detection
    if await page.locator("header").count():
        header = await page.locator("header").all_inner_texts()
        header_selector = "header"
        selectors_used.append("header")
    
    # fall back for header,
    else:
        for selector in HEADER_FALLBACK_SELECTORS:
            if await page.locator(selector).count():
                header = await page.locator(selector).all_inner_texts()
                header_selector = selector
                selectors_used.append(selector)
                break
    
    # extract href link and text from the selector
    if header_selector:
        header_text, header_link = await extract_links(page,header_selector,PAYWALL_KEYWORDS)
    if topbar_selector:
        topbar_text, topbar_link = await extract_links(page,topbar_selector,PAYWALL_KEYWORDS)

    # return the extracted information
    return {
        "selectors": selectors_used,
        "top_bar": top_bar,
        "header": header,
        "texts": header_text+topbar_text,
        "links": header_link+topbar_link,
    }