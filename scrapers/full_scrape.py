import logging
import json

from playwright.async_api import Browser

from scrapers.header import scrape_header
from scrapers.footer import scrape_footer
from scrapers.body import scrape_body
from utils import normalize_url, clean_cookies


# run for each urls; footer links and content links
async def scrape_content(browser: Browser, full_url: str, selectors: list, with_cookie=False) -> str:
    """Open a fresh page per link so DOM mutations never carry over between requests."""

    # with login cookie
    if with_cookie:
        context = await browser.new_context()
        
        # add cookies
        with open("auth.json","r") as f:
            data = json.load(f)
        data = clean_cookies(data)
        await context.add_cookies(data)

        page = await context.new_page()
    else:
        page = await browser.new_page()
    try:
        await page.goto(full_url)
        await page.wait_for_load_state("domcontentloaded")
        return await scrape_body(page, selectors)
    finally:
        await page.close()


# run for each domain
async def process_url(browser: Browser, url: str) -> dict:
    """Scraping header, footer, footer contents and body contents."""
    page = await browser.new_page()

    logging.info(f"Processing {url} ...")

    # goto url and wait unitl content load.
    await page.goto(url)
    await page.wait_for_load_state("domcontentloaded")

    # scrape header and footer
    header_data = await scrape_header(page)
    footer_data = await scrape_footer(page)

    # get the header and footer selectors to exclude while scraping contents.
    selectors = header_data["selectors"] + footer_data["selectors"]

    # scrape_body mutates the DOM (el.remove()), so we extract links
    # before closing; the page is discarded afterwards — no reuse.
    body_links = await scrape_body(page, selectors, extract_link=True)

    await page.close()

    # content pages (body links)
    content_page = []
    for link in body_links:
        full_url = normalize_url(url, link)
        try:
            logging.info(f"Processing body link {full_url} ...")

            # Fresh page every time: DOM mutations are isolated per request.
            body = await scrape_content(browser, full_url, selectors)
            content_page.append({"url": full_url, "body": body})
        except Exception as e:
            logging.error(f"Error scraping {full_url}: {e}")

    #footer pages
    footer_pages = []
    for link in footer_data.get("footer_links", []):
        full_url = normalize_url(url, link)
        try:
            logging.info(f"Processing footer link {full_url} ...")

            # Same fix: fresh page per link, no shared mutable state.
            body = await scrape_content(browser, full_url, selectors)
            footer_pages.append({"url": full_url, "body": body})
        except Exception as e:
            logging.error(f"Error scraping {full_url}: {e}")

    return {
        "header": header_data,"footer": footer_data,
        "content_page": content_page,"footer_pages": footer_pages,
    }
