from __future__ import annotations
import os
from pathlib import Path
from typing import List
import subprocess

# Placeholder TTS using system 'espeak' if available. Users can plug real TTS.

def synthesize_segments(segments: List[dict], out_dir: str | Path) -> List[str]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    audio_paths = []
    for seg in segments:
        text = seg['narration']
        fname = f"seg_{seg['idx']}.wav"
        path = out_dir / fname
        # naive espeak usage
        try:
            subprocess.run(["espeak", "-w", str(path), text], check=True)
        except FileNotFoundError:
            # fallback: create empty silent file via sox or ffmpeg
            subprocess.run(["ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "1", str(path), "-y"], check=True)
        audio_paths.append(str(path))
    return audio_paths
