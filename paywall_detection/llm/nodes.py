from __future__ import annotations

from typing import Any, Dict
import logging
import asyncio

from setup import get_page
from utils.page_utils import (
    extract_all_elements,
    manual_filter_elements,
    extract_content_by_selectors,
    extract_links_from_selectors,
    fetch_html,
    manual_filter_selectors,
)
from llm.llm_client import invoke_structured
from utils.schema import (
    CSSSelectorFilter,
    ContentLinkSelector,
    FooterLinkSelector,
    PageContent,
    PaywallPublicCheck,
    PaywallWallType,
    HeaderLoginCheck,
    LegalBasicInfo,
    PaywallInfo
)
from llm.prompt_builders import (
    build_contentlink_messages,
    build_footerlink_messages,
    build_selectors_prompt,
    build_header_login_messages,
    build_body_check_messages,
    build_footer_check_messages,
    build_wall_type_messages
)
from utils.helper import normalize_url

#TODO fallback manual filter links if many and cookies login; filter elemetents with regex (num, flex ...)
#TODO create tools, add to agent for fetching contents; just start with manual elements extraction and everyting is automation.

# Node 1 – Extract all CSS selectors from the raw HTML
async def node_extract_all_elements(state: Dict[str, Any]) -> Dict[str, Any]:
    """Discover every CSS selector present on the page."""
    logging.info("[node] extract_all_selectors")
    page = state.get("page", "")
    url = state["url"]
    if not page:
        page = await get_page()
    await page.goto(url,wait_until="domcontentloaded")
    # state["page"] = page
    state["html"] = await fetch_html(url)
    elements = await extract_all_elements(page)
    return {**state, "all_elements": elements}


# Node 2 – LLM-based selector filter  (with manual fallback)
async def node_filter_selectors(state: Dict[str, Any]) -> Dict[str, Any]:
    """Ask Gemini to classify selectors; fall back to regex rules on failure."""
    logging.info("[node] filter_selectors")
    elements = state.get("all_elements", [])
    # elements_text = "\n".join(selectors)
    if len(elements)>200:
        elements = await manual_filter_elements(elements)

    messages = build_selectors_prompt(elements)
    result = await invoke_structured(messages, CSSSelectorFilter)

    used_fallback = False
    # If the LLM returned nothing useful, fall back to manual filter
    if not (result.header_selectors or result.footer_selectors):
        logging.info("  → LLM returned empty selectors, using fallback filter")
        result = await manual_filter_selectors(state["page"],elements)
        used_fallback = True

    logging.info(
        f"→ header={len(result.header_selectors)} "
        f"footer={len(result.footer_selectors)} "
        f"excluded={len(result.excluded_selectors)} "
        f"fallback={used_fallback}"
    )
    return {**state, "filtered_selectors": result, "used_fallback_filter": used_fallback}


# Node 3 – Extract header & footer text content
async def node_extract_header_footer(state: Dict[str, Any]) -> Dict[str, Any]:
    """Pull visible text from header and footer selector zones."""
    print("[node] extract_header_footer")
    html = state.get("html","")
    if not html:
        html = await fetch_html(state["url"])
        state["html"] = html
    
    sf: CSSSelectorFilter = state["filtered_selectors"]
    excluded = sf.excluded_selectors

    header_text = await extract_content_by_selectors(
        html, sf.header_selectors, excluded=excluded
    )
    footer_text = await extract_content_by_selectors(
        html, sf.footer_selectors, excluded=excluded
    )

    logging.info(f"  → header chars={len(header_text)}  footer chars={len(footer_text)}")
    return {**state, "header_content": header_text, "footer_content": footer_text}


# Node 4 – Classify footer links
async def node_extract_footer_links(state: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and classify footer links via Gemini."""
    logging.info("[node] extract_footer_links")
    html = state["html"]
    sf: CSSSelectorFilter = state["filtered_selectors"]
    base_url = state["url"]

    hrefs, texts = await extract_links_from_selectors(
        html, sf.footer_selectors, excluded=sf.excluded_selectors
    )

    if not hrefs:
        logging.warning("  → no footer links found")
        return {**state, "footer_links": FooterLinkSelector()}

    messages = build_footerlink_messages(links=hrefs, texts=texts)
    result = await invoke_structured(messages, FooterLinkSelector)

    # Normalize all footer links
    result.privacy_links = normalize_url(base_url, result.privacy_links) if result.privacy_links else ""
    result.terms_links = normalize_url(base_url, result.terms_links) if result.terms_links else ""
    result.disclaimer_links = normalize_url(base_url, result.disclaimer_links) if result.disclaimer_links else ""

    total = sum([
        len(result.privacy_links),
        len(result.terms_links),
        len(result.disclaimer_links),
    ])
    logging.info(f"  → {total} footer links classified")
    return {**state, "footer_links": result}


# Node 5 – Classify content / body links
async def node_extract_content_links(state: Dict[str, Any]) -> Dict[str, Any]:
    """Extract and classify main-body content links via LLM."""
    
    logging.info("[node] extract_content_links")
    html = state["html"]
    base_url = state["url"]
    sf: CSSSelectorFilter = state["filtered_selectors"]

    # Remove header, footer, excluded zones before link extraction
    hrefs, texts = await extract_links_from_selectors(
        html, ["body"], excluded=sf.footer_selectors+sf.header_selectors
    )

    if not hrefs:
        logging.warning("  → no content links found")
        return {**state, "content_links": ContentLinkSelector()}

    messages = build_contentlink_messages(links=hrefs, texts=texts)
    result = await invoke_structured(messages, ContentLinkSelector)

    # Normalize all hrefs
    result.article_links = [
        normalize_url(base_url, href) for href in result.article_links]
    result.news_links = [
        normalize_url(base_url, href) for href in result.news_links]
    result.project_links = [
        normalize_url(base_url, href) for href in result.project_links]
    result.other_links = [
        normalize_url(base_url, href) for href in result.other_links]

    total = sum([
        len(result.article_links),
        len(result.news_links),
        len(result.project_links),
        len(result.other_links),
    ])
    logging.info(f"  → {total} content links classified")
    return {**state, "content_links": result}


# Node 6 – Fetch content from discovered article/news/project links
async def node_fetch_linked_content(state: Dict[str, Any]) -> Dict[str, Any]:
    """Fetch the HTML of each classified content link (up to a cap)."""
    logging.info("[node] fetch_linked_content")
 
    cl: ContentLinkSelector = state.get("content_links") or ContentLinkSelector()
    fl: FooterLinkSelector  = state.get("footer_links")  or FooterLinkSelector()
    sf: CSSSelectorFilter   = state["filtered_selectors"]
 
    # Selectors to strip so we get clean body text only
    excluded = sf.header_selectors + sf.footer_selectors
 
    sem = asyncio.Semaphore(4)
    async def _fetch_body(url: str) -> str:
        """Fetch one URL, strip header/footer noise, return clean body text."""
        async with sem:
            html = await fetch_html(url)
            if not html:
                logging.warning("  ✗ %s (empty)", url)
                return ""
            text = await extract_content_by_selectors(html,["body"], excluded=excluded)
            logging.info("  ✓ %s  body=%d chars", url, len(text))
            return text
 
    # ── Legal / footer URLs
    legal_urls = (fl.privacy_links,fl.terms_links,fl.disclaimer_links)
    # Deduplicate
    seen: set[str] = set()
    legal_urls = [u for u in legal_urls if u and not (u in seen or seen.add(u)) ]  # type: ignore
 
    # ── Content URLs (article + news + other) ─────────────────────────────────
    content_urls = (
        cl.article_links[:2]
        + cl.news_links[:2]
        + cl.other_links[:1]
    )
    seen2: set[str] = set()
    content_urls = [u for u in content_urls if not (u in seen2 or seen2.add(u))]  # type: ignore
 
    logging.info(
        "  → legal=%d urls  content=%d urls",
        len(legal_urls), len(content_urls),
    )
 
    # ── Fetch all concurrently ────────────────────────────────────────────────
    all_urls = legal_urls + content_urls
    fetched = await asyncio.gather(*[_fetch_body(u) for u in all_urls])
 
    # Split results back by group
    n_legal   = len(legal_urls)
    legal_texts   = [t for t in fetched[:n_legal]  if t]
    content_texts = [t for t in fetched[n_legal:]  if t]
 
    # Concatenate each group, truncate so LLM context stays reasonable
    footer_content = "\n\n---\n\n".join(legal_texts)[:4000]
    body_content   = "\n\n---\n\n".join(content_texts)[:6000]
 
    logging.info(
        "  → footer_content=%d chars  body_content=%d chars",
        len(footer_content), len(body_content),
    )
    page = PageContent(
        url=state["url"],
        header_content=state.get("header_content", ""),   # universal, already extracted
        footer_content=footer_content,
        body_content=body_content,
    )
 
    return {**state, "page_result": page}


# Node 6b – Check header for login info
async def node_check_header_login(state: Dict[str, Any]) -> Dict[str, Any]:
    logging.info("[node] check_header_login")
    header = state.get("header_content", "")
    if not header:
        logging.info("  → no header content, skipping")
        return {**state, "header_login": HeaderLoginCheck(
            has_login=False, has_signup=False, has_subscribe=False,
            login_text=[], reasoning="No header content available."
        )}

    result: HeaderLoginCheck = await invoke_structured(
        build_header_login_messages(url=state["url"], header_content=header),
        HeaderLoginCheck,
    )
    logging.info(
        "  → login=%s  signup=%s  subscribe=%s  labels=%s",
        result.has_login, result.has_signup, result.has_subscribe, result.login_text,
    )
    return {**state, "header_login": result}


# Node 7 – LLM paywall evaluation for each fetched page
async def node_eval_paywall_stage1(state: Dict[str, Any]) -> Dict[str, Any]:
    """Node 7 — 3 concurrent LLM zone-checks on the single PageContent."""
    logging.info("[node] eval_paywall_stage1")
    page: PageContent | None = state.get("page_result")
    if not page:
        logging.warning("  → no page_result in state, skipping")
        return state
 
    updated_page, _ = await _stage1_check_page(page)
    return {**state, "page_result": updated_page}


# Node 8 – Stage-2 paywall: wall-type classification
# Only runs for pages where is_public=False (Prompt 4)
async def node_eval_paywall_stage2(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Node 8 — For every page where is_public=False, classify wall type concurrently.
    Pages already marked public are passed through unchanged.
    """
    logging.info("[node] eval_paywall_stage2")
    page: PageContent | None = state.get("page_result")
 
    if not page:
        logging.warning("  → no page_result in state, skipping")
        return state
    
    if page.paywall.is_public:
        logging.info("  → page already marked public, skipping")
        return state
    
    cl: ContentLinkSelector = state.get("content_links") or ContentLinkSelector()
    sf: CSSSelectorFilter   = state["filtered_selectors"]
 
    # Selectors to strip so we get clean body text only
    excluded = sf.header_selectors + sf.footer_selectors
 
    sem = asyncio.Semaphore(4)
    async def _fetch_body_with_cookie(url: str) -> str:
        """Fetch one URL, strip header/footer noise, return clean body text."""
        async with sem:
            html = await fetch_html(url,with_cookie=True)
            if not html:
                logging.warning("  ✗ %s (empty)", url)
                return ""
            text = await extract_content_by_selectors(html,["body"], excluded=excluded)
            logging.info("  ✓ %s  body=%d chars", url, len(text))
            return text
 
    # ── Content URLs (article + news + other) ─────────────────────────────────
    content_urls = (
        cl.article_links[:2]+ cl.news_links[:2]+ cl.other_links[:1]
    )
    seen: set[str] = set()
    content_urls = [u for u in content_urls if not (u in seen or seen.add(u))]  # type: ignore
 
    logging.info(
        "  → content=%d urls",
        len(content_urls),
    )
 
    fetched = await asyncio.gather(*[_fetch_body_with_cookie(u) for u in content_urls])
    content_texts = [t for t in fetched if t]
 
    # Concatenate each group, truncate so LLM context stays reasonable
    body_content   = "\n\n---\n\n".join(content_texts)[:6000]
 
    logging.info(
        "  → body_content=%d chars",
        len(body_content),
    )
    page.body_content = body_content

    logging.info("  → classifying wall type")
    updated = await _classify_wall_type(page)
 
    return {**state, "page_result": updated}


async def _stage1_check_page(page: PageContent) -> tuple[PageContent, bool]:
    """
    3 concurrent LLM checks on one PageContent:
      Prompt 1 → header_content  (sign-in / subscribe buttons)
      Prompt 2 → body_content    (truncated content / overlays)
      Prompt 3 → footer_content  (membership language + legal fields)
    Majority vote (2-of-3) → is_public.
    """
    url    = page.url
    body   = page.body_content[:4000]
    footer = page.footer_content
 
    content_result, footer_result = await asyncio.gather(
        invoke_structured(
            build_body_check_messages(url=url,body_content=body),
            PaywallPublicCheck,
        ),
        invoke_structured(
            build_footer_check_messages(url=url, footer_content=footer,),
            LegalBasicInfo,
        ),
    )
 
    page.paywall = PaywallInfo(
        is_public=content_result.is_public,
        confidence=content_result.confidence,
        signals=content_result.signals,
        reasoning=content_result.reasoning,
    )
    page.legal = footer_result
    is_public = content_result.is_public
    flag = "✅ public" if is_public else "🔒 gated"
    logging.info(
        "  [%s] %s",
        flag, url
    )
    return page, is_public


async def _classify_wall_type(page: PageContent) -> PageContent:
    """Prompt 4: determine login / subscription / both for a gated page."""
    all_signals = "\n".join(page.paywall.signals) if page.paywall else ""
 
    result: PaywallWallType = await invoke_structured(
        build_wall_type_messages(
            body_content=page.body_content[:2000],
        ),
        PaywallWallType,
    )
 
    if page.paywall:
        page.paywall.wall_type       = result.wall_type
        page.paywall.wall_confidence = result.confidence
        page.paywall.wall_signals    = result.signals
        page.paywall.wall_reasoning  = result.reasoning
 
    logging.info("  🔍 %s  wall_type=%s  conf=%s", page.url, result.wall_type, result.confidence)
    return page
