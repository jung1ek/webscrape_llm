# config.py, css selectors and keyword mathing strings

PRIVACY_KEYWORDS = (
    "privacy", "privacybeleid", "cookie", "gegevensbescherming"
)

TERMS_KEYWORDS = (
    "terms", "conditions", "voorwaarden",
    "gebruiksvoorwaarden", "servicevoorwaarden"
)

DISCLAIMER_KEYWORDS = (
    "disclaimer", "aansprakelijkheid", "vrijwaring"
)

ALL_GROUPS = [
    PRIVACY_KEYWORDS,
    TERMS_KEYWORDS,
    DISCLAIMER_KEYWORDS,
]

TOPBAR_SELECTORS = [
    "#topbar", "div#topbar", ".top-bar", ".topbar",
    "#top-bar", ".header-top", ".top-header",
    ".head-top", "nav"
]

HEADER_FALLBACK_SELECTORS = [
    "#header", ".header", ".site-header",
    ".app-menu", ".modal-container"
]

FOOTER_FALLBACK_SELECTORS = [
    "#footer", ".footer", ".site-footer",
    ".footer-area", ".flex.flex-col.gap-4.w-full"
]