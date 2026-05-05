import os
from pydantic import BaseModel, Field
from typing import List

from openai import OpenAI


class SelectorCandidate(BaseModel):
    selector: str = Field(..., description="Exact CSS selector from input")


class HeaderFooterSelectors(BaseModel):
    # header_selectors: List[SelectorCandidate]
    # footer_selectors: List[SelectorCandidate]
    header_selectors: List[str] = Field(..., description="Exact CSS selectors from input")
    footer_selectors: List[str] = Field(..., description="Exact CSS selectors from input")

client = OpenAI(
    api_key=os.getenv("GOOGLE_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)

def head_foot_selector(selectors: str, tokens: str) ->HeaderFooterSelectors:
    prompt = f"""You are an expert in webpage structure analysis.

Your task is to identify the most likely CSS selectors for:
- header
- footer

You are given a list of selectors.

-----------------------------------
SEMANTIC UNDERSTANDING (IMPORTANT)
-----------------------------------

Typical HEADER selectors often look like:
- div.header
- div.site-header
- div.main-header
- div.navbar
- div.top-nav
- div.navigation
- header
- nav

Typical FOOTER selectors often look like:
- div.footer
- div.site-footer
- div.main-footer
- div.page-footer
- footer
- div.bottom
- div.site-info
- div.legal
- div.copyright

These are strong semantic patterns. Prefer selectors similar to these.

-----------------------------------
RULES
-----------------------------------

1. ONLY choose selectors from the provided list.
2. DO NOT invent new selectors.
3. Prefer selectors containing meaningful keywords:

HEADER keywords:
header, nav, navbar, top, menu

FOOTER keywords:
footer, bottom

4. Ignore generic names:
container, wrapper, box, content, grid, row, col

5. Return up to 3 candidates per category.

6. prioritize the semantic meaning fom tokens and keword match.

-----------------------------------
OUTPUT FORMAT (JSON ONLY)
-----------------------------------

{{
  "header_selectors": ["...","..."],
  "footer_selectors": ["...", "..."]
}}

-----------------------------------
INPUT SELECTORS and TOKENS:
{selectors}\n{tokens}"""
    response = client.beta.chat.completions.parse(
        model="gemini-3.1-flash-lite-preview",
        messages=[{"role": "user", "content": prompt}],
        response_format=HeaderFooterSelectors,
        max_tokens=128,
        temperature=0.7,
        reasoning_effort="none",
    )

    return response.choices[0].message.parsed