# main.py

import asyncio
import json
import logging
from dotenv import load_dotenv

load_dotenv(".env")

from playwright.async_api import async_playwright, Browser

from llm.paywall import llm_evaluation, check_post_login_paywall
from scrapers.full_scrape import process_url, scrape_content

logging.basicConfig(level=logging.INFO)

URLS = [
    "https://www.cobouw.nl",
    # "https://www.belgiumtenders.com",
    # "https://www.vlaanderen.be/",
    # "https://www.iamexpat.nl/",
    # "https://www.mil.be/nl/",
]


# ─── Phase 1: Scrape all domains ──────────────────────────────────────────────

async def scrape_phase(browser: Browser, urls: list[str]) -> dict:
    """Scrape header, footer, body links, and content for every domain."""
    results = {}
    for url in urls:
        try:
            logging.info(f"[scrape] {url}")
            results[url] = await process_url(browser, url)
        except Exception as e:
            logging.error(f"[scrape] failed for {url}: {e}")
            results[url] = {"error": str(e)}
    return results


# ─── Phase 2: LLM evaluation (public / paywall detection) ─────────────────────

def llm_phase(scrape_results: dict) -> dict:
    """Run paywall + legal LLM checks against scraped content."""
    logging.info("[llm] Running paywall and legal evaluation ...")
    return llm_evaluation(scrape_results)


# ─── Phase 3: Login-cookie scrape + subscription check ────────────────────────

async def login_phase(
    browser: Browser,
    scrape_results: dict,
    llm_results: dict,
) -> None:
    """
    For every domain that is NOT public, re-scrape with auth cookie,
    then run check_post_login_paywall and attach the result in-place.
    """
    for domain, paywall in llm_results.items():
        if paywall.get("access", {}).get("is_public", True):
            continue  # already public — nothing more to check

        try:
            logging.info(f"[login] {domain}")

            domain_data = scrape_results.get(domain, {})
            selectors = (
                domain_data.get("header", {}).get("selectors", [])
                + domain_data.get("footer", {}).get("selectors", [])
            )

            # Scrape every content-page URL using the stored auth cookie
            bodies: list[str] = []
            for content in domain_data.get("content_page", []):
                url = content.get("url")
                if not url:
                    continue
                body = await scrape_content(browser, url, selectors, with_cookie=True)
                if body:
                    bodies.append(body)
                await asyncio.sleep(2)  # rate-limit between requests

            combined_body = "\n\n".join(bodies)

            # Subscription-level paywall check (True = still blocked after login)
            sub_paywall = check_post_login_paywall(combined_body)
            logging.info(f"[login] sub_paywall={sub_paywall} for {domain}")

            llm_results[domain]["access"]["subscription_paywall"] = sub_paywall

        except Exception as e:
            logging.error(f"[login] failed for {domain}: {e}")
            llm_results[domain]["access"]["subscription_paywall"] = None


# ─── Orchestrator ──────────────────────────────────────────────────────────────

async def main() -> None:

    # ── Phase 1: scrape ──────────────────────────────────────────────────────
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        scrape_results = await scrape_phase(browser, URLS)
        await browser.close()

    with open("scrape_result.json", "w", encoding="utf-8") as f:
        json.dump(scrape_results, f, indent=2, ensure_ascii=False)
    logging.info("[scrape] results saved → scrape_result.json")

    # ── Phase 2: LLM ─────────────────────────────────────────────────────────
    llm_results = llm_phase(scrape_results)

    # ── Phase 3: login scrape (only non-public domains) ──────────────────────
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        await login_phase(browser, scrape_results, llm_results)
        await browser.close()

    # ── Final output ─────────────────────────────────────────────────────────
    with open("llm_result.json", "w", encoding="utf-8") as f:
        json.dump(llm_results, f, indent=2, ensure_ascii=False)
    logging.info("[done] final results saved → llm_result.json")

    # print(json.dumps(llm_results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())