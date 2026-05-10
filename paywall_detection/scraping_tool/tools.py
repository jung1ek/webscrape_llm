from __future__ import annotations
from typing import List, Optional, Type, Dict, Any
from pydantic import BaseModel, Field
import logging

from langchain.tools import BaseTool
from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from crawl4ai.content_filter_strategy import PruningContentFilter
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator

from utils.helper import *

class CrawlInput(BaseModel):
    html: str = Field(..., description="Raw HTML content")

    selectors: Optional[List[str]] = Field(
        default=None,
        description="CSS selectors to include / target"
    )

    exclude_selectors: Optional[List[str]] = Field(
        default=None,
        description="CSS selectors to exclude/remove"
    )

#TODO use single single selectors , keep appending based on result.
class CrawlHTMLTool(BaseTool):
    name: str = "crawl_html_tool"
    description: str = (
        "Extract clean markdown and links from raw HTML using Crawl4AI. "
        "Supports include selectors and exclude selectors."
    )

    args_schema : Type[BaseModel] = CrawlInput

    async def _arun(self, html: str, selectors: Optional[List[str]]=None,
                    exclude_selectors: Optional[List[str]]=None):
        
        content_filter = PruningContentFilter(threshold=0.45,
            threshold_type="dynamic",min_word_threshold=5,
        )
        config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS,

            # exclude these selectors
            excluded_selector=", ".join(exclude_selectors or []),

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

            return {
                "markdown": result.markdown,
                "internal_links": result.links.get("internal", []),
                "external_links": result.links.get("external", []),
            }

        except Exception as e:
            raise RuntimeError(f"Error while scraping HTML: {e}")
        
    def _run(self, *args, **kwargs):
        raise NotImplementedError(
            "This tool only supports async execution."
        )
    

class ExtractLinksInput(BaseModel):
    result: Dict[str, Any] = Field(..., description="Crawler output with internal/external links")
    validate_keywords: List[str] = Field(..., description="Keywords to filter relevant links")
    footer_link: bool = Field(False, description="Whether to extract footer links or main links")


class ExtractLinksTool(BaseTool):
    name: str = "extract_links"
    description: str = "Extracts and filters links from crawler output using keyword matching"
    args_schema: Type[BaseTool] = ExtractLinksInput

    def _run(self, result, validate_keywords, footer_link=False):

        texts, urls = [], []
        seen = set()
        keyword_used = set()

        internal = result.get("internal_links", [])
        external = result.get("external_links", [])
        all_links = internal + external

        def score_link(text, href):
            text = (text or "").lower()
            href = (href or "").lower()

            return sum(
                2 if k in text else 1 if k in href else 0
                for k in validate_keywords
            )

        # rank best matches first
        all_links.sort(
            key=lambda l: score_link(l.get("text"), l.get("href")),
            reverse=True
        )

        for link in all_links:
            try:
                text = (link.get("text") or "").strip()
                href = (link.get("href") or "").strip().lower()

                if not href or href in seen:
                    continue

                if not is_valid_link(href):
                    continue

                seen.add(href)

                matched_keyword = next(
                    (k for k in validate_keywords
                     if (k in href or k in text.lower())
                     and k not in keyword_used),
                    None,
                )

                if not matched_keyword:
                    continue

                # limit main links
                if not footer_link and len(urls) >= 2:
                    break

                # avoid shallow duplicate nav links
                path_parts = [
                    p for p in urlparse(href).path.strip("/").split("/")
                    if p
                ]

                if path_parts and len(path_parts) == 1:
                    if matched_keyword in path_parts[-1]:
                        continue

                keyword_used.add(matched_keyword)
                texts.append(text)
                urls.append(href)

            except Exception as e:
                logging.warning(f"Skipping link: {e}")

        return {"texts": texts, "urls": urls}

    async def _arun(self, *args, **kwargs):
        raise NotImplementedError("Async not required for this tool")
