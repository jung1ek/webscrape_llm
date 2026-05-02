# main.py

import asyncio
import json
import logging
from dotenv import load_dotenv

load_dotenv(".env")

from playwright.async_api import async_playwright
from playwright.async_api import Browser

from scrapers.header import scrape_header
from scrapers.footer import scrape_footer
from scrapers.body import scrape_body
from utils import normalize_url

logging.basicConfig(level=logging.INFO)

PAGE_TIMEOUT = 30_000
CONTENT_TIMEOUT = 20_000

URLS = [
    "https://www.cobouw.nl",
    "https://www.belgiumtenders.com",
    "https://www.vlaanderen.be/",
    "https://www.iamexpat.nl/",
    "https://www.mil.be/nl/",
]


# run for each urls; footer links and content links
async def scrape_link(browser: Browser, full_url: str, selectors: list) -> str:
    """Open a fresh page per link so DOM mutations never carry over between requests."""
    page = await browser.new_page()
    try:
        await page.goto(full_url)
        await page.wait_for_load_state("domcontentloaded")
        return await scrape_body(page, selectors)
    finally:
        await page.close()


# run for each domain
async def process_url(browser: Browser, url: str) -> dict:
    page = await browser.new_page()

    logging.info(f"Processing {url} ...")

    await page.goto(url)
    await page.wait_for_load_state("domcontentloaded")

    header_data = await scrape_header(page)
    footer_data = await scrape_footer(page)

    selectors = header_data["selectors"] + footer_data["selectors"]

    # scrape_body mutates the DOM (el.remove()), so we extract links
    # before closing; the page is discarded afterwards — no reuse.
    body_links = await scrape_body(page, selectors, extract_link=True)

    await page.close()

    # --- content pages (body links) ---
    content_page = []
    for link in body_links:
        full_url = normalize_url(url, link)
        try:
            logging.info(f"Processing body link {full_url} ...")
            # Fresh page every time: DOM mutations are isolated per request.
            body = await scrape_link(browser, full_url, selectors)
            content_page.append({"url": full_url, "body": body})
        except Exception as e:
            logging.error(f"Error scraping {full_url}: {e}")

    # --- footer pages ---
    footer_pages = []
    for link in footer_data.get("footer_links", []):
        full_url = normalize_url(url, link)
        try:
            logging.info(f"Processing footer link {full_url} ...")
            # Same fix: fresh page per link, no shared mutable state.
            body = await scrape_link(browser, full_url, selectors)
            footer_pages.append({"url": full_url, "body": body})
        except Exception as e:
            logging.error(f"Error scraping {full_url}: {e}")

    return {
        "header": header_data,
        "footer": footer_data,
        "content_page": content_page,
        "footer_pages": footer_pages,
    }


async def main():
    results = {}

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)

        # for each domains
        for url in URLS:
            try:
                results[url] = await process_url(browser, url)
            except Exception as e:
                logging.error(f"Error processing {url}: {e}")
                results[url] = {"error": str(e)}

        await browser.close()

    # save results in json file
    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())