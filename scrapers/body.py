# scrapers/body.py

from typing import Union
from playwright.async_api import Page

from utils import extract_links
from config import NEWS_KEYWORDS, PROJECT_KEYWORDS


async def scrape_body(page, selectors_to_remove: list, extract_link: bool = False) -> Union[str,list]:
    """Extract clean body text after removing header/footer."""
    
    # clear header and footer from the selectors
    for selector in selectors_to_remove:
        await page.locator(selector).evaluate_all(
            "els => els.forEach(el => el.remove())"
        )

    # extracting body content and body links
    if await page.locator("body").count():
        if extract_link:
            texts, urls = await extract_links(page,"body",NEWS_KEYWORDS+PROJECT_KEYWORDS)
            return urls
        else:
            return await page.locator("body").inner_text()

    return ""