# llm/paywall.py

import os
from typing import List
from pydantic import BaseModel, Field
from openai import OpenAI

# OpenAi client object
client = OpenAI(
    api_key=os.getenv("GOOGLE_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)


# Paywall info model
class PaywallInfo(BaseModel):
    has_paywall: bool = Field(...,
        description="True if content is blocked or restricted behind login/subscription.")
    login_paywall = Field(...,
        description=""),
    has_login: bool = Field(...,
        description="True if login/signup in header.")
    popup_login: bool = Field(...,
        description="True if login/signup in not in header.")
    confidence: str = Field(...,
        description="Confidence level: high, medium, or low.")
    signals: List[str] = Field(...,
        description="Detected signals indicating paywall or login wall.")
    reasoning: str = Field(...,
        description="Short explanation comparing header and body content.")


# legality evaluation model
class LegalBasicInfo(BaseModel):
    has_terms: bool
    has_privacy: bool
    allows_scraping: bool
    reasoning: str


def check_paywall(header_context: str, body_context: str) -> PaywallInfo:
    """Analyze header + body to detect paywall or login walls."""

    prompt = f"""
You are analyzing a webpage to detect access restrictions.

You are given:
1. HEADER CONTENT → navigation, login/signup buttons
2. BODY CONTENT → actual visible page content

Determine:

- has_login_wall = TRUE if:
  - login/signup required ("sign in", "log in", "create account")
  - auth-related links dominate access

- has_paywall = TRUE if:
  - content is blocked, blurred, or truncated
  - "subscribe to read", "upgrade to continue"
  - little or no readable content

- BOTH can be true.

- FALSE if:
  - body contains real, readable content
  - no blocking messages

Be strict and realistic.

HEADER:
{header_context}

BODY:
{body_context}
"""

    response = client.beta.chat.completions.parse(
        model="gemini-3.1-flash-lite-preview",
        messages=[{"role": "user", "content": prompt}],
        response_format=PaywallInfo,
        max_tokens=1024,
        reasoning_effort="none",
    )

    return response.choices[0].message.parsed


def check_legal_basic(terms_privacy_text: str) -> LegalBasicInfo:
    """Minimal legal check: terms, privacy, scraping allowance, reasoning."""

    prompt = f"""
Analyze the following website legal texts.

Return:

- has_terms = TRUE if Terms of Service content is clearly present
- has_privacy = TRUE if Privacy Policy content is clearly present

- allows_scraping = TRUE if explicitly allows:
  scraping, crawling, bots, automated access, or APIs
- allows_scraping = FALSE if:
  prohibits scraping, bots, automation, or data extraction
- If not mentioned → FALSE

- reasoning = short (1–2 lines), concrete justification

Be strict. Do not assume anything not explicitly stated.

TERMS and PRIVACY: \n
{terms_privacy_text}
"""

    response = client.beta.chat.completions.parse(
        model="gemini-3.1-flash-lite-preview",
        messages=[{"role": "user", "content": prompt}],
        response_format=LegalBasicInfo,
        max_tokens=1024,
        reasoning_effort="none",
    )

    return response.choices[0].message.parsed


def safe_join(value):
    if isinstance(value, list):
        return " ".join(str(v) for v in value if v)
    if isinstance(value, str):
        return value
    return ""


def llm_evaluation(scrape_results: dict):
    results = {}

    # go through every domain
    for url, data in scrape_results.items():
        try:

            # extract footer, header and content from scraped data
            footer_pages = data.get("footer_pages", [])
            header = data.get("header",{})
            content_pages = data.get("content_page", [])

            # Concatenate all footer page bodies
            header_text = "\n\n".join([
                safe_join(header.get("top_bar")),safe_join(header.get("header")),
                safe_join(header.get("texts")),safe_join(header.get("links")),
            ])

            combined_text = "\n\n".join(
                page.get("body", "") for page in footer_pages if page.get("body"))

            body_text = "\n\n".join(
                page.get("body", "") for page in content_pages if page.get("body"))


            # Truncate (important for speed + cost)
            header_text = header_text.strip()[:8000]
            body_text = body_text.strip()[100:12000]
            combined_text = combined_text[100:12000]

            # Send same text as both terms + privacy, and header + content info
            legal_info = check_legal_basic(terms_privacy_text=combined_text)
            paywall_info = check_paywall(header_context=header_text, body_context=body_text)

            results[url] = {
                "legal_terms": {
                    "has_terms": legal_info.has_terms,"has_privacy": legal_info.has_privacy,
                    "allows_scraping": legal_info.allows_scraping,"reasoning": legal_info.reasoning,
                },
                "paywall":{
                    "has_login": paywall_info.has_login,"has_paywall": paywall_info.has_paywall,
                    "confidence": paywall_info.confidence,"signals": paywall_info.signals,
                    "reasoning": paywall_info.reasoning,"popup_login": paywall_info.popup_login
                }
            }
        except Exception as e:
            results[url] = {"error": str(e)}
    return results
