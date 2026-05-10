from __future__ import annotations
from typing import Any, Dict

from langgraph.graph import END, StateGraph

from setup import get_page
from llm.nodes import *


#Build the graph 
def build_graph() -> StateGraph:
    """
    Pipeline topology
    """

    # Use plain dict as state
    graph = StateGraph(dict)

    graph.add_node("extract_all_selectors", node_extract_all_elements)
    graph.add_node("filter_selectors", node_filter_selectors)

    graph.set_entry_point("extract_all_selectors")
    graph.add_edge("extract_all_selectors", "filter_selectors")

    graph.add_node("extract_header_footer", node_extract_header_footer)
    graph.add_node("extract_footer_links", node_extract_footer_links)
    graph.add_node("extract_content_links", node_extract_content_links)

    graph.add_edge("filter_selectors", "extract_header_footer")
    graph.add_edge("extract_header_footer", "extract_footer_links")
    graph.add_edge("extract_footer_links", "extract_content_links")


    graph.add_node("fetch_contents", node_fetch_linked_content)
    graph.add_node("eval_paywall", node_eval_paywall_stage1)
    graph.add_node("header_login", node_check_header_login)
    graph.add_node("eval_paywall_type", node_eval_paywall_stage2)
    
    graph.add_edge("extract_content_links", "fetch_contents")
    graph.add_edge("fetch_contents", "header_login")
    graph.add_edge("header_login", "eval_paywall")
    graph.add_edge("eval_paywall", "eval_paywall_type")
    graph.add_edge("eval_paywall_type", END)

    return graph.compile()


# Convenience runner 
async def run_pipeline(url: str,raw_html: str = "") -> Dict[str, Any]:
    """Async entry point — run the full pipeline for *url*."""
    app = build_graph()
    page = await get_page()
    
    initial: Dict[str, Any] = {
            "url": url,
            "page": page,
            "html": raw_html,
            "all_selectors": [],
            "filtered_selectors": None,
            "used_fallback_filter": False,
            "header_content": "",
            "footer_content": "",
            "footer_links": None,
            "content_links": None,
            "page_result": None,
            "errors": [],
      }

    print(f"\n{'='*64}")
    logging.info(f"  Pipeline start: {url}")
    print(f"{'='*64}\n")
 
    final = await app.ainvoke(initial)
 
    print(f"\n{'='*64}")
    print("  Pipeline complete")
    print(f"{'='*64}\n")
    
    return final
 
