import logging
from typing import List

from playwright.async_api import Page
from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

from utils.helper import *
from setup import get_page
from utils.schema import CSSSelectorFilter

logging.basicConfig(level=logging.INFO)

async def fetch_html(url:str, timeout: int =15)-> str:
    try:
        logging.info(f"Goto url: {url}")
        page = await get_page()
        await page.goto(url,wait_until="domcontentloaded",timeout=timeout*1000)
        html = await page.locator("body").inner_html()
        return html
    except Exception as e:
        logging.error(f"[fetch_html] failed for {url}: {e}")
        return ""
    

async def extract_all_elements(page: Page) -> List[str]:
    try:
        elements = await get_elements(page)
        logging.info(f"Found {len(elements)} elements.")
        return elements
    except Exception as e:
        logging.error(f"Error while Extracting elements: {e}")
        raise

async def manual_filter_elements(elements, strict=False)-> List[str]:
    if elements:
        filterd_els = [el for el in elements if is_specific("",el)]
        if strict:
            filterd_els = [el for el in filterd_els if is_header_like(el) or is_footer_like(el)]
            logging.info(f"Filtered {len(elements)} elements >> {len(filterd_els)} elements.")
        return filterd_els
    else:
        logging.error(f"Eelements not extracted")
        []


async def manual_filter_selectors(page,elements: List[str],top=0.10,bottom=0.90):
    """Fallback: rule-based selector classification (no LLM)."""
    if elements:
        doc_height = await page.evaluate("document.documentElement.scrollHeight")
        header_cut = doc_height * top
        footer_cut = doc_height * bottom
        # header: semantic first, position fallback 
        header_els = [el for el in elements if is_header_like(el)]
        if not header_els:
            header_els = [el for el in elements if el["mid_y"] < header_cut]

        header_set = {id(el) for el in header_els}

        # everything from 90% to bottom, regardless of how big the middle is
        footer_els = [el for el in elements if is_footer_like(el)]
        if not footer_els:
            footer_els = [el for el in elements if id(el) not in header_set
                # and el["top"] >= footer_cut     # top edge, not mid_y
                and el["mid_y"] >= footer_cut ]

        logging.info(f"Header elements: {len(header_els)}.")
        logging.info(f"Footer elements: {len(footer_els)}.")

        footer_selectors = list({build_selector(el) for el in footer_els \
                                if is_specific(build_selector(el),el)})
        header_selectors   = list({build_selector(el) for el in header_els \
                                if is_specific(build_selector(el),el)})
        logging.info(f"Header Selectors: {len(header_selectors)}.")
        logging.info(f"Footer Selectors: {len(footer_selectors)}.")


        return CSSSelectorFilter(header_selectors=header_selectors,
                                 footer_selectors=footer_selectors,
                                 excluded_selectors=[])
    else:
        logging.error(f"Eelements not extracted")
        return CSSSelectorFilter(header_selectors=[],footer_selectors=[],excluded_selectors=[])


async def extract_content_by_selectors(html,selectors,excluded=[]):

    content_filter = PruningContentFilter(threshold=0.45,
            threshold_type="dynamic",min_word_threshold=5,
        )
    config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS,

        # exclude these selectors
        excluded_selector=", ".join(excluded or []),

        # include only these selectors
        target_elements=selectors or [],

        # text and links
        word_count_threshold=1,only_text=False,
        exclude_external_links=True,
        exclude_social_media_links=True,
        exclude_internal_links=False,

        # strip noise
        excluded_tags=["script","style","noscript",
            "iframe","svg","img","video","audio",
            "form","button",
        ],
        remove_forms=True,
        markdown_generator=DefaultMarkdownGenerator(
            content_filter=content_filter,
            options={
                "ignore_images": True,
                "ignore_tables": True,
                "body_width": 0,
            },
        ),
    )
    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(
                url=f"raw:{html}",config=config,
            )

        return result.markdown

    except Exception as e:
        logging.error(f"Error while scraping HTML: {e}")
        return ""


async def extract_links_from_selectors(
    html,
    selectors,
    base_url,
    excluded=None
):
    excluded = excluded or []

    content_filter = PruningContentFilter(
        threshold=0.45,
        threshold_type="dynamic",
        min_word_threshold=5,
    )

    config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,

        # include selectors
        target_elements=selectors or [],

        # exclude selectors
        excluded_selector=", ".join(excluded),

        # links
        word_count_threshold=1,
        only_text=False,

        exclude_external_links=True,
        exclude_social_media_links=True,
        exclude_internal_links=False,

        # remove noise
        excluded_tags=[
            "script", "style", "noscript",
            "iframe", "svg", "img",
            "video", "audio",
            "form", "button",
        ],

        remove_forms=True,

        markdown_generator=DefaultMarkdownGenerator(
            content_filter=content_filter,
            options={
                "ignore_images": True,
                "ignore_tables": True,
                "body_width": 0,
            },
        ),
    )

    try:
        async with AsyncWebCrawler() as crawler:
            result = await crawler.arun(
                url=f"raw:{html}",
                config=config,
            )

        hrefs = []
        texts = []
        seen = set()

        links = result.links.get("internal", [])

        for link in links:

            href = link.get("href", "")
            text = (link.get("text") or "").strip()

            # # normalize relative -> absolute
            # href = normalize_url(base_url, raw_href)

            # validate
            if not is_valid_link(href):
                continue

            # dedupe
            if href in seen:
                continue

            seen.add(href)

            hrefs.append(href)
            texts.append(text)

        return hrefs, texts

    except Exception as e:
        raise RuntimeError(f"Error extracting links: {e}")
    


class ElementExtraction():

    def __init__(self,url,elements):
        self.url = url
        self.elements = elements
        self.header = None
        self.footer = None

        self.header_sels = None
        self.footer_sels = None

    def __repr__(self):
        return f"URL: {self.url} >> H: {self.header_sels} || F: {self.footer_sels}"


    @classmethod
    async def extract_manual_filter_selectors(cls,page: Page, url: str,top: float=0.05, bottom: float=0.95):
        try:
            logging.info(f"Goto url: {url}")
            await page.goto(url,wait_until="domcontentloaded")
            doc_height = await page.evaluate("document.documentElement.scrollHeight")
            header_cut = doc_height * top
            footer_cut = doc_height * bottom

            elements = await get_elements(page)
            logging.info(f"Found {len(elements)} elements.")
            
            # header: semantic first, position fallback 
            header_els = [el for el in elements if is_header_like(el)]
            if not header_els:
                header_els = [el for el in elements if el["mid_y"] < header_cut]

            header_set = {id(el) for el in header_els}

            # everything from 90% to bottom, regardless of how big the middle is
            footer_els = [el for el in elements if is_footer_like(el)]
            if not footer_els:
                footer_els = [el for el in elements if id(el) not in header_set
                    # and el["top"] >= footer_cut     # top edge, not mid_y
                    and el["mid_y"] >= footer_cut ]

            logging.info(f"Header elements: {len(header_els)}.")
            logging.info(f"Footer elements: {len(footer_els)}.")

            footer_selectors = list({build_selector(el) for el in footer_els \
                                    if is_specific(build_selector(el),el)})
            header_selectors   = list({build_selector(el) for el in header_els \
                                    if is_specific(build_selector(el),el)})
            logging.info(f"Header Selectors: {len(header_selectors)}.")
            logging.info(f"Footer Selectors: {len(footer_selectors)}.")

            out = cls(url,elements)

            out.header = header_els
            out.footer = footer_els

            out.header_sels = header_selectors
            out.footer_sels = footer_selectors
            return out
        except Exception as e:
            logging.error(f"Error while Extracting elements: {e}")
            raise
    
    @classmethod
    async def extract_elements(cls,page: Page, url: str):
        try:
            logging.info(f"Goto url: {url}")
            await page.goto(url,wait_until="domcontentloaded")

            elements = await get_elements(page)
            logging.info(f"Found {len(elements)} elements.")
            return cls(url,elements)
        except Exception as e:
            logging.error(f"Error while Extracting elements: {e}")
            raise
    
    def manual_filter_elements(self,strict: bool=False):
        if self.elements:
            filterd_els = [el for el in self.elements if is_specific("",el)]
            if strict:
                filterd_els = [el for el in filterd_els if is_header_like(el) or is_footer_like(el)]
            logging.info(f"Filtered {len(self.elements)} elements >> {len(filterd_els)} elements.")
            self.elements = filterd_els
        else:
            logging.error(f"Eelements not extracted")
        
