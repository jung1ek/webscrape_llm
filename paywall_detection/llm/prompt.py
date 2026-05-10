from typing import Final

class PaywallPrompt:

    HEADER_LOGIN_SYSTEM: Final[str] = """You are a UI analyst checking a webpage header for authentication controls.

Look for: login, sign in, log in, register, sign up, create account, subscribe, upgrade buttons or links.

Return ONLY JSON (no prose):
{{
  "has_login": bool,
  "has_signup": bool,
  "has_subscribe": bool,
  "login_text": ["exact label", ...],
  "reasoning": "..."
}}"""

    HEADER_LOGIN_HUMAN: Final[str] = """Page URL: {url}

Header text:
{header_content}

Detect authentication controls."""

    PAYWALL_SYSTEM_PROMPT: Final[str] = """You are a paywall-detection specialist.
Given the visible text content of a webpage, decide whether the page is behind a
paywall or requires a subscription / login to read the full content.
 
Signals of a paywall:
  - "Subscribe to read", "Members only", "Sign in to continue"
  - Abruptly truncated article body
  - Overlay / modal language asking for payment or account creation
 
Return a JSON object with two keys:
  • is_paywalled (bool)
  • confidence   (float 0-1)
 
No prose, only JSON."""
 
    PAYWALL_HUMAN_PROMPT: Final[str] = """Page URL: {url}
 
Visible content (first 3000 chars):
{content}
 
Is this page paywalled?"""

    WALL_TYPE_SYSTEM: Final[str] = """You are a paywall-type classifier.
The page has already been confirmed as NOT freely accessible.
Determine the exact type of gate based on the content I provide after login/access attempts.
 
Possible classifications:
 
  "login"        – free account required (no payment).
  "subscription" – paid plan required (credit card, no free tier).
  "both"         – must create account AND pay.
 
Signals to look for:
  login-only  : "Create a free account", "Register to read", social login.
  subscription: "Subscribe from $X/month", "Choose a plan", pricing table.
  both        : login page leads to a pricing page, or both signals present.
 
Return ONLY a JSON object (no prose, no markdown):
{{
  "wall_type": "login"|"subscription"|"both",
  "confidence": "high"|"medium"|"low",
  "signals": ["..."],
  "reasoning": "..."
}}"""
 
    WALL_TYPE_HUMAN: Final[str] = """
 
Body content (first 2000 chars):
{body_content}
 
Classify the wall type."""


    FOOTER_LEGAL_SYSTEM: Final[str] = """You are a legal analyst reading a webpage footer and its linked legal pages.

Determine:
  has_terms      : is there a Terms of Service / Terms & Conditions link or text?
  has_privacy    : is there a Privacy Policy link or text?
  allows_scraping: does the visible terms text ban automated/scraping access?
                   Default true if no terms text is visible.

Return ONLY JSON (no prose, no markdown):
{{
  "has_terms": bool,
  "has_privacy": bool,
  "allows_scraping": bool,
  "reasoning": "..."
}}"""

    FOOTER_LEGAL_HUMAN: Final[str] = """Page URL: {url}

Footer text:
{footer_content}

Determine legal info."""


class LinksPrompt:

    FOOTER_LINK_PROMPT = """
You are a link extraction system.

Task: Identify ONLY footer/legal links from a list of links.

Return structured group of link:

PRIVACY KEYWORDS:
privacy, privacybeleid, cookie, gegevensbescherming

TERMS KEYWORDS:
terms, conditions, voorwaarden, gebruiksvoorwaarden, servicevoorwaarden

DISCLAIMER KEYWORDS:
disclaimer, aansprakelijkheid, vrijwaring

Rules:
- Match based on URL OR visible text
- Prefer exact semantic match over partial match
- Ignore navigation, blog, or article links
- Only return link that clearly belong to legal/footer section
    - If unsure, exclude
"""
    CONTENT_LINK_PROMPT: Final[str] = """
You are an intelligent web link classifier.

Your task is to classify links into:

---

ARTICLE KEYWORDS:
English:
article, blog, post, story, insight, publication, write-up
Dutch:
artikel, blog, bericht, verhaal, inzichten, publicatie

---

NEWS KEYWORDS:
Dutch:
nieuws, laatste, update, pers, aankondiging, kop
English:
news, latest, update, press, announcement, headline, breaking

---

PROJECT KEYWORDS:
English:
project, case study, portfolio, work, client work, implementation, deployment
Dutch:
project, case, portfolio, werk, klantcase, implementatie, realisatie

---

RULES:
- Use BOTH href and visible text
- Prefer semantic meaning over keyword match
- Detect paywall indicators (e.g. "subscribe", "premium", "login") and EXCLUDE those links
- Avoid navigation, footer, legal, or category pages
- Only include meaningful content pages
- If ambiguous, classify as other_links
"""
    CSS_SELECTOR_PROMPT = """
You are a CSS selector optimization system.

You will receive a list of DOM elements with:
- id
- class
- tag
- text content

Task:
Group selectors into:

1. HEADER SELECTORS
- navigation bars
- top menus
- site headers
- branding areas

2. FOOTER SELECTORS
- bottom navigation
- legal links section
- cookie/privacy/terms sections

3. BODY SELECTORS
- main article content
- blog/news content
- product/project content

4. EXCLUDED SELECTORS
- ads
- popups
- modals
- cookie banners
- login overlays

RULES:
- Prefer structural tags (header, nav, footer, main, article)
- Prefer stable selectors (id > class > tag)
- Avoid overly generic selectors (e.g. div, span alone)
- Avoid dynamic/generated class names if possible
- Select minimal set of selectors that capture full region
- If uncertain, exclude rather than include
"""
    CSS_SELECTOR_SYSTEM_PROMPT = """
You are a CSS selector extraction system.

You receive DOM elements with structured attributes.

Your task is to generate accurate, minimal, and NON-OVERLAPPING CSS selectors.

---

## ELEMENT FIELDS YOU WILL SEE

Each element contains:

IDENTITY:
- tag
- id
- class
- name
- role

CONTENT:
- text (trimmed)
- href
- src
- alt
- title

ARIA:
- aria_label
- aria_role
- aria_expanded
- aria_hidden
- aria_current

FORM:
- input_type
- value
- action

POSITION:
- top
- mid_y
- left
- width
- height

LAYOUT:
- position
- z_index
- display

STRUCTURE:
- depth

---

## TASK

Group elements into:

- header_selectors
- footer_selectors
- body_selectors
- excluded_selectors

---

## CRITICAL RULE: NO OVERLAP

- A selector must NOT overlap with another selector's coverage
- If a parent selector already captures child elements, DO NOT include child selector
- If a more specific selector exists, DO NOT include a broader one that duplicates content

Example:
❌ BAD:
header
header nav

✔ GOOD:
header nav

OR (depending on specificity):
header

but NEVER both if they overlap content

---

## CATEGORY RULES

HEADER:
- role = navigation / banner
- class contains: nav, header, menu, top
- depth: low (0–3)
- high z_index
- grouped links

FOOTER:
- role = contentinfo
- class contains: footer
- high top value (bottom of page)
- contains keywords:
  privacy, terms, cookie, conditions, disclaimer

EXCLUDED:
- popup, overlay
- cookie banner, ads
- dialog, alerts
- high z_index blocking UI
- tag: article, main, section
- class contains: article, content, post, blog, news, project
- higher depth
- meaningful text content

---

## SELECTOR RULES

- Prefer id over class over tag
- Prefer stable structural selectors (header/nav/footer/)
- Avoid generic selectors like div/span alone
- Avoid content body selectors (article/main)
- Avoid dynamic/hashed class names if possible
- Return minimal selectors with maximum coverage

---

## OUTPUT FORMAT (STRICT JSON)

{{
  "header_selectors": [],
  "footer_selectors": [],
  "excluded_selectors": []
}}
"""
    CSS_SELECTOR_HUMAN_PROMPT: Final[str] ="""
Analyze the following DOM elements and generate CSS selectors.

Rules:
- Ensure selectors are unique and non-overlapping
- Do not create redundant parent-child selectors
- Use only necessary selectors for full coverage
- Prefer stability and specificity

Elements:

{elements}

"""

ELEMENT_EXTRACTOR_JS: Final[str] = """
() => {
    const ALLOWED_TAGS = new Set([
        'div', 'header', 'footer', 'section', 'nav'
    ]);

    const results = [];

    for (const el of document.body.querySelectorAll('*')) {
        const tag = el.tagName.toLowerCase();

        // only structural elements
        if (!ALLOWED_TAGS.has(tag)) continue;

        const rect   = el.getBoundingClientRect();
        const scrollY = window.scrollY || 0;
        const absTop  = rect.top + scrollY;
        const midY    = absTop + rect.height / 2;
        const style   = window.getComputedStyle(el);

        // skip invisible / zero-size elements
        if (rect.width === 0 || rect.height === 0)  continue;
        if (style.display === 'none')                continue;
        if (style.visibility === 'hidden')           continue;
        if (parseFloat(style.opacity) === 0)         continue;

        results.push({
            // identity
            tag,
            id:          el.id                        || null,
            class:       el.className                 || null,
            name:        el.getAttribute('name')      || null,
            role:        el.getAttribute('role')      || null,

            // content
            text:        el.innerText?.trim().slice(0, 200) || null,
            href:        el.getAttribute('href')      || null,
            src:         el.getAttribute('src')       || null,
            alt:         el.getAttribute('alt')       || null,
            title:       el.getAttribute('title')     || null,
            //placeholder: el.getAttribute('placeholder') || null,

            // aria
            aria_label:    el.getAttribute('aria-label')    || null,
            aria_role:     el.getAttribute('aria-role')     || null,
            aria_expanded: el.getAttribute('aria-expanded') || null,
            aria_hidden:   el.getAttribute('aria-hidden')   || null,
            aria_current:  el.getAttribute('aria-current')  || null,

            // form
            input_type: tag === 'input' ? el.getAttribute('type') : null,
            value:      el.getAttribute('value')  || null,
            action:     el.getAttribute('action') || null,

            // position
            top:    Math.round(absTop),
            mid_y:  Math.round(midY),
            left:   Math.round(rect.left),
            width:  Math.round(rect.width),
            height: Math.round(rect.height),

            // layout signals
            position: style.position,
            z_index:  parseInt(style.zIndex) || 0,
            display:  style.display,

            // dom depth
            depth: (function() {
                let d = 0, p = el;
                while (p.parentElement) { d++; p = p.parentElement; }
                return d;
            })(),
        });
    }

    return results;
}
"""