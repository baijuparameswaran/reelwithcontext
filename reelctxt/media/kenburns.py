from __future__ import annotations
from typing import Tuple

def ken_burns_filter(duration: float, zoom: float = 1.1) -> str:
    # Simple scale + slight pan using ffmpeg zoompan filter placeholder
    fps = 30
    return f"zoompan=z='min(zoom+0.0005*in, {zoom})':d={int(duration*fps)}:fps={fps}"
