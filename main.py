# main.py

import asyncio
import json
import logging
from dotenv import load_dotenv

load_dotenv(".env")

from playwright.async_api import async_playwright
from playwright.async_api import Browser

from llm.paywall import llm_evaluation
from scrapers.full_scrape import process_url

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


async def main():
    # scrape results
    results = {}

    # playwright run
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
    with open("ccrape_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # llm response result
    llm_results = llm_evaluation(results)

    with open("llm_results.json", "w", encoding="utf-8") as f:
        json.dump(llm_results, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    asyncio.run(main())