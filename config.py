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
    "#topbar", "div#topbar",".top-bar", ".topbar",
    "#top-bar", ".header-top", ".top-header", ".head-top","nav"
]

HEADER_FALLBACK_SELECTORS = [
    "#header", ".header", ".site-header", ".app-menu", "#modal-container"
]

FOOTER_FALLBACK_SELECTORS = [
    "#footer", ".footer", ".site-footer",".footer-area",
    ".flex.flex-col.gap-4.w-full"
]

ARTICLE_KEYWORDS = (
    # English
    "article", "blog", "post", "story", "insight",
    "publication", "write-up",

    # Dutch
    "artikel", "blog", "bericht", "verhaal", "inzichten",
    "publicatie"
)

NEWS_KEYWORDS = (
    # English
    "news", "latest", "update", "press", "announcement",
    "headline", "breaking",

    # Dutch
    "nieuws", "laatste", "update", "pers", "aankondiging",
    "kop", "breaking"
)

PROJECT_KEYWORDS = (
    # English
    "project", "case study", "portfolio", "work", "client work",
    "implementation", "deployment",

    # Dutch
    "project", "case", "portfolio", "werk", "klantcase",
    "implementatie", "realisatie"
)

PAYWALL_KEYWORDS = (
    "sign", "log", "auth", "try"
)

ALL_CONTENT_GROUPS = [
    NEWS_KEYWORDS,
    ARTICLE_KEYWORDS,
    PROJECT_KEYWORDS, 
]