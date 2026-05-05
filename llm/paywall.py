import os
from typing import List, Literal
from pydantic import BaseModel, Field
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("GOOGLE_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)


class PaywallInfo(BaseModel):
    # Stage 1: Is content freely readable without any account?
    is_public: bool = Field(...,
        description="True if real, readable content is visible without login or payment.")

    # Stage 2: If not public — what kind of wall?
    wall_type: Literal["none", "login", "subscription", "both"] = Field(...,
        description=(
            "'none' if public. "
            "'login' if free account required. "
            "'subscription' if paid plan required. "
            "'both' if login AND payment required."
        ))

    confidence: Literal["high", "medium", "low"] = Field(...,
        description="Confidence in the classification.")

    signals: List[str] = Field(...,
        description="Detected signals: e.g. 'subscribe to read', 'blurred content', 'sign in button'.")

    reasoning: str = Field(...,
        description="Short explanation of why this classification was chosen.")


class LegalBasicInfo(BaseModel):
    has_terms: bool
    has_privacy: bool
    allows_scraping: bool
    reasoning: str


def check_paywall(header_context: str, body_context: str) -> PaywallInfo:
    """
    3-stage detection:
      Stage 1 → is content public (no wall at all)?
      Stage 2 → login wall (free account needed)?
      Stage 3 → subscription/pay wall?
    """

    prompt = f"""
You are analyzing a webpage to classify its access model.

You are given:
1. HEADER CONTENT → navigation bar, login/signup buttons, menu links
2. BODY CONTENT → actual visible page content

---

Classify using this strict decision tree:

STEP 1 — Is content PUBLIC?
  → is_public = TRUE if:
     - Body contains real, readable, substantive content
     - No blocking, blurring, or truncation messages
     - No "sign in to read", "subscribe to continue" etc.
  → is_public = FALSE otherwise → go to STEP 2

STEP 2 — What type of wall?
  → wall_type = "login" if:
     - Content is accessible after creating a FREE account
     - Signals: "sign in", "log in", "create free account", "join for free"
     - No mention of payment or subscription

  → wall_type = "subscription" if:
     - Content requires PAYMENT to access
     - Signals: "subscribe", "upgrade", "premium", "$X/month", "paywall"
     - No free login option offered

  → wall_type = "both" if:
     - Login is required AND subscription/payment is also required

  → wall_type = "none" ONLY if is_public = TRUE

---

HEADER:
{header_context}

BODY:
{body_context}
"""

    response = client.beta.chat.completions.parse(
        model="gemini-3.1-flash-lite-preview",
        messages=[{"role": "user", "content": prompt}],
        response_format=PaywallInfo,
        max_tokens=512,
        reasoning_effort="none",
    )

    return response.choices[0].message.parsed


def check_legal_basic(terms_privacy_text: str) -> LegalBasicInfo:
    prompt = f"""
Analyze the following website legal texts.

Return:
- has_terms = TRUE if Terms of Service content is clearly present
- has_privacy = TRUE if Privacy Policy content is clearly present
- allows_scraping = TRUE only if explicitly allows scraping, crawling, bots, or automated access
- allows_scraping = FALSE if prohibited or not mentioned
- reasoning = 1–2 lines, concrete justification

Be strict. Do not assume anything not explicitly stated.

TERMS and PRIVACY:
{terms_privacy_text}
"""

    response = client.beta.chat.completions.parse(
        model="gemini-3.1-flash-lite-preview",
        messages=[{"role": "user", "content": prompt}],
        response_format=LegalBasicInfo,
        max_tokens=512,
        reasoning_effort="none",
    )

    return response.choices[0].message.parsed


def check_post_login_paywall(body_context: str) -> bool:
    """Returns sub_paywall=False if real content exists after login."""
    
    prompt = f"""
You are given the body content of a webpage after a user has logged in.

Is there real, substantive, readable content on this page?
Answer only: YES or NO

- YES → content is accessible (no subscription needed)
- NO  → content is still blocked (subscription required)

BODY:
{body_context}
"""
    response = client.chat.completions.create(
        model="gemini-3.1-flash-lite-preview",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=8,
    )

    answer = response.choices[0].message.content.strip().upper()
    return answer == "NO"  # sub_paywall=True if still blockeds


def safe_join(value):
    if isinstance(value, list):
        return " ".join(str(v) for v in value if v)
    if isinstance(value, str):
        return value
    return ""


def llm_evaluation(scrape_results: dict):
    """LLM Evaluation"""
    results = {}

    for url, data in scrape_results.items():
        try:
            footer_pages  = data.get("footer_pages", [])
            header        = data.get("header", {})
            content_pages = data.get("content_page", [])

            header_text = "\n\n".join([safe_join(header.get("top_bar")),
                safe_join(header.get("header")),safe_join(header.get("texts")),
                safe_join(header.get("links")),]).strip()[:8000]

            body_text = "\n\n".join(
                page.get("body", "") for page in content_pages if page.get("body")
            ).strip()[100:12000]

            combined_text = "\n\n".join(
                page.get("body", "") for page in footer_pages if page.get("body")
            )[100:12000]

            # --- Stage 1+2+3 in one LLM call ---
            paywall_info = check_paywall(
                header_context=header_text,
                body_context=body_text
            )

            # --- Legal check (only if content seems accessible) ---
            legal_info = check_legal_basic(terms_privacy_text=combined_text)

            results[url] = {
                "access": {
                    "is_public": paywall_info.is_public,"wall_type": paywall_info.wall_type,  
                    "confidence": paywall_info.confidence,"signals": paywall_info.signals,
                    "reasoning": paywall_info.reasoning,
                },
                "legal_terms": {
                    "has_terms": legal_info.has_terms,"has_privacy": legal_info.has_privacy,
                    "allows_scraping": legal_info.allows_scraping,"reasoning": legal_info.reasoning,
                },
            }

        except Exception as e:
            results[url] = {"error": str(e)}

    return results