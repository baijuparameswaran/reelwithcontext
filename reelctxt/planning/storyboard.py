from __future__ import annotations
from typing import List
from ..llm.client import LLMClient
from .segment import Segment, normalize_segments


def build_storyboard(prompt: str, summary: str, segments: int, llm: LLMClient) -> List[Segment]:
    raw = llm.storyboard(prompt, summary, segments=segments)
    return normalize_segments(raw)
