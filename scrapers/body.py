# scrapers/body.py

from typing import Union

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

from utils import extract_links
from config import NEWS_KEYWORDS, PROJECT_KEYWORDS, ARTICLE_KEYWORDS


async def scrape_body(page, selectors_to_remove: list, extract_link: bool = False) -> Union[str,list]:
    """Extract clean body text after removing header/footer."""
    
    # clear header and footer from the selectors
    for selector in selectors_to_remove:
        await page.locator(selector).evaluate_all(
            "els => els.forEach(el => el.remove())"
        )

     # Extract the cleaned HTML from the live page
    html = await page.locator("body").inner_html()

    # Feed it straight to Crawl4AI — no second browser needed
    config = CrawlerRunConfig(
        # Disable JS execution — HTML is already rendered
        js_code=None,
        wait_for=None,
        exclude_external_links=True,
        exclude_internal_links=True
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url=f"raw:{html}",   # "raw:" prefix tells Crawl4AI it's literal HTML
            config=config,
            
        )

    # extracting body content and body links
    if await page.locator("body").count():
        if extract_link:
            _, urls = await extract_links(page,"body",NEWS_KEYWORDS+ARTICLE_KEYWORDS+PROJECT_KEYWORDS)
            return urls
        else:
            return result.markdown

    return ""