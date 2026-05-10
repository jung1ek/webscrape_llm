from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class FooterLinkSelector(BaseModel):
    privacy_links: str = Field(
        default_factory=str,
        description="Link related to privacy, cookies, and data protection"
    )

    terms_links: str = Field(
        default_factory=str,
        description="Link related to terms, conditions, and service policies"
    )

    disclaimer_links: str = Field(
        default_factory=str,
        description="Link related to disclaimers or legal liability"
    )


class ContentLinkSelector(BaseModel):
    article_links: List[str] = Field(
        default_factory=list,
        description="Blog/article/content links"
    )

    news_links: List[str] = Field(
        default_factory=list,
        description="News, updates, announcements, press releases"
    )

    project_links: List[str] = Field(
        default_factory=list,
        description="Portfolio, case studies, client work, projects"
    )

    other_links: List[str] = Field(
        default_factory=list,
        description="Fallback relevant links not matching above categories"
    )


class CSSSelectorFilter(BaseModel):
    header_selectors: List[str] = Field(
        default_factory=list,
        description="Selectors targeting header/navigation areas"
    )

    footer_selectors: List[str] = Field(
        default_factory=list,
        description="Selectors targeting footer/legal/navigation bottom areas"
    )

    excluded_selectors: List[str] = Field(
        default_factory=list,
        description="Selectors that should be removed (ads, popups, etc.)"
    )


# ── Legal / scraping policy  and login checks
class HeaderLoginCheck(BaseModel):
    has_login: bool = Field(..., description="True if a login/sign-in button or link is present in the header.")
    has_signup: bool = Field(..., description="True if a register/sign-up/create account button is present.")
    has_subscribe: bool = Field(..., description="True if a subscribe/upgrade CTA is present in the header.")
    login_text: List[str] = Field(default_factory=list, description="Exact button/link labels found, e.g. ['Sign in', 'Log in'].")
    reasoning: str

class LegalBasicInfo(BaseModel):
    has_terms: bool = Field(..., description="Site has a Terms of Service page.")
    has_privacy: bool = Field(..., description="Site has a Privacy Policy page.")
    allows_scraping: bool = Field(
        ...,
        description=(
            "True if scraping / automated access is NOT explicitly forbidden. "
            "False if ToS or robots.txt-style language bans it."
        ),
    )
    reasoning: str = Field(..., description="One-sentence explanation.")
 
 
# ── Stage-1 paywall: is content publicly readable? ────────────────────────────
 
class PaywallPublicCheck(BaseModel):
    """
    LLM prompt 1 (header signal) + prompt 2 (body signal) feed into this.
    Each prompt returns one of these independently; they are merged in the node.
    """
    is_public: bool = Field(
        ...,
        description="True if real, readable content is visible without login or payment.",
    )
    confidence: Literal["high", "medium", "low"] = Field(
        ..., description="Confidence in the classification."
    )
    signals: List[str] = Field(
        ...,
        description=(
            "Detected signals, e.g. 'subscribe to read', "
            "'blurred content', 'sign-in button in header'."
        ),
    )
    reasoning: str = Field(
        ..., description="Short explanation of why this classification was chosen."
    )
 
 
# ── Stage-2 paywall: what kind of wall? (only if not public) ─────────────────
 
class PaywallWallType(BaseModel):
    wall_type: Literal["login", "subscription", "both"] = Field(
        ...,
        description=(
            "'login' = free account required. "
            "'subscription' = paid plan required. "
            "'both' = login AND payment required."
        ),
    )
    confidence: Literal["high", "medium", "low"]
    signals: List[str]
    reasoning: str
 
 
# ── Merged result per page ────────────────────────────────────────────────────
 
class PaywallInfo(BaseModel):
    is_public: bool
    confidence: Literal["high", "medium", "low"]
    signals: List[str] = Field(default_factory=list)
    reasoning: str = ""
    # Only populated when is_public=False
    wall_type: Optional[Literal["login", "subscription", "both"]] = None
    wall_confidence: Optional[Literal["high", "medium", "low"]] = None
    wall_signals: List[str] = Field(default_factory=list)
    wall_reasoning: str = ""
 
 
# ── Single fetched page with 3 zones ─────────────────────────────────────────
 
class PageContent(BaseModel):
    url: str
    # Universal header text (nav/branding) — same across the site
    header_content: str = ""
    # Concatenated legal footer text: privacy + terms + disclaimer pages joined
    footer_content: str = ""
    # Concatenated main content: article + news + other pages joined
    body_content: str = ""
    # Paywall verdict
    paywall: Optional[PaywallInfo] = None
    legal: Optional[LegalBasicInfo] = None

 
# ── Pipeline state ────────────────────────────────────────────────────────────
 
class PipelineState(BaseModel):
    url: str = ""
    raw_html: str = ""
 
    all_selectors: List[str] = Field(default_factory=list)
    filtered_selectors: Optional[CSSSelectorFilter] = None
    used_fallback_filter: bool = False
 
    header_content: str = ""
    footer_content: str = ""
 
    footer_links: Optional[FooterLinkSelector] = None
    content_links: Optional[ContentLinkSelector] = None
 
    extracted_pages: List[PageContent] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
 
    class Config:
        arbitrary_types_allowed = True
 
