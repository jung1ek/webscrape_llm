# scrapers/footer.py

from playwright.async_api import Page

from config import FOOTER_FALLBACK_SELECTORS
from utils import is_valid_link, matches_keywords


async def scrape_footer(page: Page) -> dict:
    """Extract footer and important legal links."""
    selectors_used = []
    footer_selector = None
    footer_text = None

    # Primary footer
    if await page.locator("footer").count():
        footer_selector = "footer"
        selectors_used.append("footer")
        footer_text = await page.locator("footer").last.inner_text()
    # fallback for footer
    else:
        for selector in FOOTER_FALLBACK_SELECTORS:
            if await page.locator(selector).count():
                footer_selector = selector
                selectors_used.append(selector)
                footer_text = await page.locator(selector).last.inner_text()
                break
    
    # link's text and href
    links_out, texts_out = [], []

    # extracting links
    if footer_selector:
        links = page.locator(f"{footer_selector} a")

        for i in range(await links.count()):
            text = (await links.nth(i).inner_text()).lower()
            href = (await links.nth(i).get_attribute("href") or "").lower()

            if not is_valid_link(href):
                continue

            if matches_keywords(href) or matches_keywords(text):
                links_out.append(href)
                texts_out.append(text)

    return {
        "selectors": selectors_used,
        "footer": footer_text,
        "footer_links": links_out,
        "text_links": texts_out,
    }