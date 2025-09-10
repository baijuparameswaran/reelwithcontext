from __future__ import annotations
import urllib.parse as urlparse
from collections import deque
from dataclasses import dataclass
from typing import List, Set
from bs4 import BeautifulSoup
import requests
import logging

logger = logging.getLogger(__name__)

@dataclass
class CrawledPage:
    url: str
    text: str


def same_domain(seed: str, target: str) -> bool:
    s = urlparse.urlparse(seed)
    t = urlparse.urlparse(target)
    return (s.netloc == t.netloc) and t.scheme in {"http", "https"}


def crawl(start_url: str, max_pages: int = 10, max_depth: int = 1) -> List[CrawledPage]:
    visited: Set[str] = set()
    q = deque([(start_url, 0)])
    out: List[CrawledPage] = []
    headers = {"User-Agent": "ReelCtxtCrawler/0.1"}

    while q and len(out) < max_pages:
        url, depth = q.popleft()
        if url in visited or depth > max_depth:
            continue
        visited.add(url)
        try:
            r = requests.get(url, headers=headers, timeout=15)
            r.raise_for_status()
        except Exception as e:
            logger.warning("Failed %s: %s", url, e)
            continue
        ct = r.headers.get('content-type', '')
        if 'text/html' not in ct:
            continue
        soup = BeautifulSoup(r.text, 'html.parser')
        for tag in soup(['script', 'style', 'noscript']):
            tag.decompose()
        text = soup.get_text(separator=' ', strip=True)
        out.append(CrawledPage(url=url, text=text))
        if depth < max_depth:
            for a in soup.find_all('a', href=True):
                href = urlparse.urljoin(url, a['href'])
                if same_domain(start_url, href) and href not in visited:
                    q.append((href, depth + 1))
    return out
