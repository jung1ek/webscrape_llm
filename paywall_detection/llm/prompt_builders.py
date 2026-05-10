from __future__ import annotations
import logging

from langchain_core.prompts import ChatPromptTemplate

from llm.prompt import *

selector_prompt = ChatPromptTemplate.from_messages([
    ("system", LinksPrompt.CSS_SELECTOR_SYSTEM_PROMPT),
    ("human", LinksPrompt.CSS_SELECTOR_HUMAN_PROMPT),
])

def build_selectors_prompt(elements):
    messages = selector_prompt.format_messages(**{"elements":elements})
    return messages


FOOT_USER_PROMPT: Final[str] = "Links (href) and Text: \n{links}\n\n{texts}"

footerlink_prompt = ChatPromptTemplate.from_messages([
    ("system", LinksPrompt.FOOTER_LINK_PROMPT),
    ("human", FOOT_USER_PROMPT),
])

def build_footerlink_messages(links: str, texts: str):
    messages = footerlink_prompt.format_messages(links=links, texts=texts)
    return messages


CON_USER_PROMPT: Final[str] = "Links (href) and Text: \n{links}\n{texts}"

contentlink_prompt = ChatPromptTemplate.from_messages([
    ("system", LinksPrompt.CONTENT_LINK_PROMPT),
    ("human", CON_USER_PROMPT),
])
 
def build_contentlink_messages(links: str, texts: str):
    messages = contentlink_prompt.format_messages(links=links, texts=texts)
    return messages


# ── Paywall prompt 1: header check ───────────────────────────────────────────

_header_login_prompt = ChatPromptTemplate.from_messages([
    ("system", PaywallPrompt.HEADER_LOGIN_SYSTEM),
    ("human", PaywallPrompt.HEADER_LOGIN_HUMAN),
])

def build_header_login_messages(url: str, header_content: str):
    msgs = _header_login_prompt.format_messages(url=url, header_content=header_content)
    return msgs
 
 
# ── Paywall prompt 2: body check ─────────────────────────────────────────────
 
_body_check_prompt = ChatPromptTemplate.from_messages([
    ("system", PaywallPrompt.PAYWALL_SYSTEM_PROMPT),
    ("human", PaywallPrompt.PAYWALL_HUMAN_PROMPT),
])
 
 
def build_body_check_messages(url: str, body_content: str):
    msgs = _body_check_prompt.format_messages(url=url, content=body_content)
    logging.info(f"[prompt:body_check] ~{len(str(msgs))} chars")
    return msgs
 
# ── Paywall prompt 3: footer + legal check ───────────────────────────────────
 
_footer_check_prompt = ChatPromptTemplate.from_messages([
    ("system", PaywallPrompt.FOOTER_LEGAL_SYSTEM),
    ("human", PaywallPrompt.FOOTER_LEGAL_HUMAN),
])
 
 
def build_footer_check_messages(url: str, footer_content: str):
    msgs = _footer_check_prompt.format_messages(
        url=url, footer_content=footer_content,
    )
    print(f"[prompt:footer_check] ~{len(str(msgs))} chars")
    return msgs
 
 
# ── Paywall prompt 4: wall-type classification ────────────────────────────────
 
_wall_type_prompt = ChatPromptTemplate.from_messages([
    ("system", PaywallPrompt.WALL_TYPE_SYSTEM),
    ("human", PaywallPrompt.WALL_TYPE_HUMAN),
])
 
 
def build_wall_type_messages(body_content: str,):
    msgs = _wall_type_prompt.format_messages(
        body_content=body_content,
    )
    print(f"[prompt:wall_type] ~{len(str(msgs))} chars")
    return msgs

 

