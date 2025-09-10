from __future__ import annotations
import os
from pathlib import Path
from typing import Iterable, List, Dict
import logging
from bs4 import BeautifulSoup
import requests

TEXT_EXTS = {".txt", ".md", ".markdown", ".html", ".htm"}

logger = logging.getLogger(__name__)

def load_text_from_files(folder: str | Path) -> List[Dict]:
    """Recursively load text files and return list of {path, content}."""
    folder = Path(folder)
    results: List[Dict] = []
    if not folder.exists():
        logger.warning("Text folder %s does not exist", folder)
        return results
    for p in folder.rglob('*'):
        if p.is_file() and p.suffix.lower() in TEXT_EXTS:
            try:
                text = p.read_text(encoding='utf-8', errors='ignore')
                if p.suffix.lower() in {'.html', '.htm'}:
                    soup = BeautifulSoup(text, 'html.parser')
                    text = soup.get_text(separator=' ', strip=True)
                results.append({"path": str(p), "content": text})
            except Exception as e:
                logger.error("Failed reading %s: %s", p, e)
    return results

def fetch_url(url: str, timeout: int = 15) -> str | None:
    try:
        resp = requests.get(url, timeout=timeout, headers={'User-Agent': 'ReelCtxtBot/0.1'})
        resp.raise_for_status()
        ct = resp.headers.get('content-type', '')
        if 'text/html' not in ct:
            return None
        soup = BeautifulSoup(resp.text, 'html.parser')
        # remove script/style
        for tag in soup(['script', 'style', 'noscript']):
            tag.decompose()
        return soup.get_text(separator=' ', strip=True)
    except Exception as e:
        logger.warning("Fetch failed %s: %s", url, e)
        return None
