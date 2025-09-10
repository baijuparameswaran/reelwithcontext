from __future__ import annotations
from pathlib import Path
from typing import List, Dict
import logging
from PIL import Image

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp'}
logger = logging.getLogger(__name__)

def load_images(folder: str | Path, max_dim: int = 512) -> List[Dict]:
    folder = Path(folder)
    out: List[Dict] = []
    if not folder.exists():
        logger.warning("Image folder %s not found", folder)
        return out
    for p in folder.rglob('*'):
        if p.is_file() and p.suffix.lower() in IMAGE_EXTS:
            try:
                with Image.open(p) as im:
                    im = im.convert('RGB')
                    w, h = im.size
                    scale = max_dim / max(w, h)
                    if scale < 1:
                        new_size = (int(w*scale), int(h*scale))
                        im = im.resize(new_size)
                    out.append({
                        'path': str(p),
                        'width': im.width,
                        'height': im.height,
                        'thumbnail': im  # kept in memory; small
                    })
            except Exception as e:
                logger.error("Failed image %s: %s", p, e)
    return out
