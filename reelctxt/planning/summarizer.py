from __future__ import annotations
from typing import List
from ..llm.client import LLMClient


def build_summary(prompt: str, corpus_texts: List[str], llm: LLMClient) -> str:
    return llm.summarize(prompt, corpus_texts)
