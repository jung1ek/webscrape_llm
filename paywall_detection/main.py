from __future__ import annotations

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime, UTC
from dotenv import load_dotenv
from typing import Dict, List, Any

load_dotenv(".env")

from llm.graph import run_pipeline
from utils.schema import PageContent, PaywallInfo
from setup import get_page,close_browser
from utils.schema import *

def save_state_to_json(state, filename="crawl_results.json"):
    """
    Append crawl results to a JSON file.
    Creates file if it doesn't exist.
    """

    output = {
        "timestamp": datetime.now(UTC).isoformat(),

        "url": state.get("url"),

        "selectors": {},
        "footer_links": {},
        "content_links": {},

        "pages": [],
    }

    header = state.get("header_content")
    if header:
        output["header"] = header
    
    footer = state.get("footer_content")
    if footer:
        output["footer"] = footer

    # selectors
    sf = state.get("filtered_selectors")
    if sf:
        output["selectors"] = {
            "header_selectors": sf.header_selectors,
            "footer_selectors": sf.footer_selectors,
            "excluded_selectors": sf.excluded_selectors,
        }

    # footer links
    fl = state.get("footer_links")
    if fl:
        output["footer_links"] = {
            "privacy_links": fl.privacy_links,
            "terms_links": fl.terms_links,
            "disclaimer_links": getattr(fl, "disclaimer_links", ""),
        }

    # content links
    cl = state.get("content_links")
    if cl:
        output["content_links"] = {
            "article_links": cl.article_links,
            "news_links": cl.news_links,
            "project_links": cl.project_links,
            "other_links": cl.other_links,
        }
    
    print("\n____ LOGIN CHECKS ──────────────────────────────────────")
    hl: HeaderLoginCheck = state.get("header_login")
    if hl:
        output["header_login"]={
            "has_login": hl.has_login,
            "has_signup": hl.has_signup,
            "has_subscribe": hl.has_subscribe,
            "login_text": hl.login_text
        }

    print("\n── PAYWALL RESULTS ──────────────────────────────────────")
    p: PageContent = state.get("page_result", None)
    if p.paywall:
        output["paywall_summary"] = {
            "is_public": p.paywall.is_public,
            "confidence": p.paywall.confidence,
            "signals": p.paywall.signals,
            "reasoning": p.paywall.reasoning,
            "wall_type": p.paywall.wall_type,
            "wall_confidence": p.paywall.wall_confidence,
            "wall_signals": p.paywall.wall_signals,
            "wall_reasoning": p.paywall.wall_reasoning,
        }

    # extracted pages
    
    if p.legal:
        output["legal"] = {
            "has_terms": p.legal.has_terms,
            "has_privacy": p.legal.has_privacy,
            "allows_scraping": p.legal.allows_scraping,
        }


    path = Path(filename)

    # existing file
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, list):
                data = []

        except Exception:
            data = []

    else:
        data = []

    # append new run
    data.append(output)

    # save
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved results → {filename}")

def _paywall_summary(p: PageContent) -> str:
    pw: PaywallInfo | None = p.paywall
    if not pw:
        return "  no paywall data"
    flag = "✅ public" if pw.is_public else f"🔒 gated [{pw.wall_type or '?'}]"
    return (
        f"  {flag}  conf={pw.confidence}\n"
        f"  signals : {pw.signals[:3]}\n"
        f"  reason  : {pw.reasoning[:120]}"
    )


URLS = [
    # "https://www.cobouw.nl",
    "https://www.belgiumtenders.com",
    "https://www.vlaanderen.be/",
    "https://www.iamexpat.nl/",
    "https://www.mil.be/nl/",
]

async def main():
    for url in URLS:
        await run(url) # this will run the pipeline.
    await close_browser()
    
async def run(url) -> None:
    # url = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
 
    state = await run_pipeline(url)

    print("\n── SELECTORS ────────────────────────────────────────────")
    sf = state.get("filtered_selectors")
    if sf:
        print(f"  header   : {sf.header_selectors[:4]}")
        print(f"  footer   : {sf.footer_selectors[:4]}")
        print(f"  excluded : {sf.excluded_selectors[:4]}")

    print("\n── FOOTER LINKS ─────────────────────────────────────────")
    fl = state.get("footer_links")
    if fl:
        print(f"  privacy  : {fl.privacy_links}")
        print(f"  terms    : {fl.terms_links}")

    print("\n── CONTENT LINKS ────────────────────────────────────────")
    cl = state.get("content_links")
    if cl:
        print(f"  articles : {cl.article_links[:3]}")
        print(f"  news     : {cl.news_links[:3]}")
        print(f"  projects : {cl.project_links[:3]}")

    print("\n____ LOGIN CHECKS ──────────────────────────────────────")
    hl: HeaderLoginCheck = state.get("header_login")
    if hl:
        print(f"  has_login: {hl.has_login}")
        print(f"  has_signup: {hl.has_signup}") 
    

    print("\n── PAYWALL RESULTS ──────────────────────────────────────")
    p: PageContent = state.get("page_result", None)
    if p:
        print(f"\n  {p.url}")
        print(_paywall_summary(p))
        print(
            f"  legal → terms={p.legal.has_terms}  \n"
            f"privacy={p.legal.has_privacy}  \n"
            f"scraping_ok={p.legal.allows_scraping}\n"
            f"reasoning={p.legal.reasoning[:120]}\n"
        )
        print(
            f" is public={p.paywall.is_public}  \n"
            f"wall_type={p.paywall.wall_type}  \n"
            f"confidence={p.paywall.confidence}  \n"
            f"reasoning={p.paywall.reasoning[:120]} \n"
        )
    
    save_state_to_json(state)

if __name__ == "__main__":
    asyncio.run(main())
