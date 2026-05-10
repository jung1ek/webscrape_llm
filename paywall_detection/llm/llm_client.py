from __future__ import annotations

import os
from typing import Type, TypeVar
import time
import logging

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


def get_llm() -> ChatGoogleGenerativeAI:
    """Returns a Google Generative AI LLM client."""
    return ChatGoogleGenerativeAI(
        model="gemini-3.1-flash-lite-preview",
        google_api_key=os.environ["GOOGLE_API_KEY"],
        temperature=0.0,
        max_output_tokens=1024,
    )


async def invoke_structured(
    messages,
    schema: Type[T],
    llm: ChatGoogleGenerativeAI | None = None,
) -> T:
    """Invoke the LLM with structured output."""
    _llm = llm or get_llm()

    for attempt in range(3):
        try:
            structured_llm = _llm.with_structured_output(schema)
            return structured_llm.invoke(messages)
        except Exception as exc:
            logging.error(f"Failed to invoke LLM: {exc}")
            time.sleep(2 ** attempt)