from __future__ import annotations
import os
from typing import List
from openai import OpenAI

DEFAULT_MODEL = os.getenv("REELCTXT_LLM_MODEL", "gpt-4o-mini")

class LLMClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None):
        api_key = api_key or os.getenv("OPENAI_API_KEY")
        base_url = base_url or os.getenv("REELCTXT_LLM_ENDPOINT")
        self.model = model or DEFAULT_MODEL
        self.client = OpenAI(api_key=api_key, base_url=base_url) if api_key else None

    def available(self) -> bool:
        return self.client is not None

    def summarize(self, prompt: str, texts: List[str], max_words: int = 180) -> str:
        joined = "\n".join(t[:4000] for t in texts)[:12000]
        sys_msg = (
            "You are a concise assistant producing a compact expert summary focused on key actionable points. "
            f"Max {max_words} words."
        )
        if not self.client:
            # fallback naive
            return " ".join(joined.split()[:max_words])
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": f"PROMPT: {prompt}\nCONTEXT:\n{joined}"}
            ],
            temperature=0.4,
        )
        return resp.choices[0].message.content.strip()

    def storyboard(self, prompt: str, summary: str, segments: int = 6) -> List[dict]:
        if not self.client:
            # simple deterministic split
            words = summary.split()
            chunk = max(1, len(words)//segments)
            sb = []
            for i in range(segments):
                part = words[i*chunk:(i+1)*chunk]
                if not part:
                    break
                sb.append({
                    'idx': i,
                    'narration': ' '.join(part),
                    'title': f'Segment {i+1}',
                    'hint': ''
                })
            return sb
        sys_msg = "Create a JSON array; each element: {idx, title, narration, hint}. Narration <= 18 words, energetic, vertical reel tone."
        user_content = f"PROMPT: {prompt}\nSUMMARY: {summary}\nSEGMENTS: {segments}"
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": sys_msg}, {"role": "user", "content": user_content}],
            temperature=0.6,
        )
        import json
        txt = resp.choices[0].message.content
        try:
            data = json.loads(txt)
            assert isinstance(data, list)
            return data
        except Exception:
            return [{'idx': i, 'title': f'Segment {i+1}', 'narration': line, 'hint': ''} for i, line in enumerate(summary.split('.')[:segments])]
