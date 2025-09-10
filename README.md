# ReelCtxt

ReelCtxt is a command-line application to generate short "reel" style videos from:

- A natural language prompt (theme / intent)
- A context corpus consisting of:
  - Local images (folder tree)
  - Local text documents (markdown, txt, html) (folder tree)
  - Remote blog / portal URLs (recursively crawled within same domain, optional depth)

It performs:
1. Crawl & ingest context (text + image metadata)
2. Summarize & extract key beats relevant to the prompt using an LLM (pluggable)
3. Auto-generate a storyboard (segments with narration + matching visuals)
4. Synthesize narration audio (TTS engine pluggable)
5. Compose vertical video (1080x1920) with:
   - Background media (image pan/zoom or short clips if present)
   - Caption overlays (word-level timing if available)
   - Optional background music track ducked under narration
6. Export final MP4 + JSON sidecar (storyboard + timings)

---
## Features (Initial Scope)
- Local ingestion (images + text)
- Basic URL crawling (same-domain, depth=1 default)
- OpenAI-compatible LLM abstraction (can be replaced with offline model calls)
- Storyboard planner (simple beat extraction)
- Image selection heuristic (semantic similarity using embeddings)
- Ken Burns effect for still images
- FFmpeg-based composition pipeline
- Background music with optional sidechain ducking
- Automatic caption overlays (title or narration) and fallback colored frames when no images
- Optional Ken Burns slow zoom effect on still images
 - Continuous music bed across all segments (disable with --no-continuous-music)
 - Intro / outro music stems, music fade in/out, and narration loudness normalization
- CLI interface `reelctxt`

---
## Roadmap (Future Enhancements)
- Video clip support
- Multi-language narration
- Advanced styling templates
- Music mood selection
- Scene transition variety
- Interactive web UI

---
## Contributing / Next Enhancements
Below are near-term, low-risk improvements that can meaningfully elevate the quality of the generated reels:

1. Segment dataclass + schema validation (ensures consistent fields and catches missing images early)
2. Additional unit tests (crawler domain restriction, storyboard fallback, duration estimator edge cases)
3. Music support (optional background track with auto ducking beneath narration)
4. Graceful fallback visual (solid color background with overlay text when no image match)
5. CLIP / vision embeddings for semantically better image selection
6. Real TTS provider plugin (e.g., ElevenLabs, Azure, or local models) with caching
7. Configurable templates (font, safe margins, caption styles, transitions)
8. Docker packaging for reproducible rendering environment

Let me know if you’d like any of the suggested enhancements implemented now (e.g., segment dataclass, more tests, music support) and we can iterate immediately.

---
## Installation (Editable)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage
Example:
```bash
reelctxt \
  --prompt "Top 5 benefits of serverless architecture" \
  --text-folder ./samples/text \
  --image-folder ./samples/images \
  --url https://example.com/blog/serverless-intro \
  --output out/video.mp4
    --music assets/music/ambient.mp3 --music-volume 0.25
```

Dry run (no rendering, just prints storyboard):
```bash
reelctxt --prompt "AI in agriculture" --text-folder ./docs --image-folder ./imgs --dry-run
```

Add background music with ducking (default enabled):
```bash
reelctxt --prompt "Cloud cost optimization tips" \
  --text-folder ./docs --image-folder ./imgs \
  --music ./audio/bed.mp3 --music-volume 0.18
```
Disable ducking:
```bash
reelctxt --prompt "Edge caching explained" --music ./audio/bed.mp3 --no-duck
```

Use a single continuous music bed (default). To revert to per-segment looping:
```bash
reelctxt --prompt "Container security essentials" --music ./audio/bed.mp3 --no-continuous-music
```

Add intro & outro stems with fades and voice normalization:
```bash
reelctxt --prompt "Modern data pipeline in 60s" \
  --music ./audio/bed.mp3 \
  --music-intro ./audio/intro.wav \
  --music-outro ./audio/outro.wav \
  --fade-in 2.0 --fade-out 2.5 \
  --music-volume 0.22
```

Disable loudness normalization:
```bash
reelctxt --prompt "Async Python patterns" --music ./audio/bed.mp3 --no-voice-normalize
```

Keep intermediate build artifacts for debugging:
```bash
reelctxt --prompt "Observability in microservices" --music ./audio/bed.mp3 --keep-temp
```

Force clean previous temp directory before build:
```bash
reelctxt --prompt "Event-driven architecture" --pre-cleanup
```

Disable captions and rely only on narration:
```bash
reelctxt --prompt "Zero trust basics" --no-captions
```

Use narration text for captions, custom font and colors:
```bash
reelctxt --prompt "API security pitfalls" \
  --caption-mode narration \
  --caption-font ./fonts/Inter-Bold.ttf \
  --caption-color '#ffeecc' \
  --caption-box-color '0x000000@0.6'
```

Enable Ken Burns effect:
```bash
reelctxt --prompt "Quantum computing basics" --image-folder ./imgs --ken-burns --ken-burns-zoom 1.1
```

---
## Configuration
Environment variables:
- OPENAI_API_KEY (if using OpenAI-compatible endpoint)
- REELCTXT_LLM_ENDPOINT (override base URL)
- REELCTXT_LLM_MODEL (model name, default: gpt-4o-mini)

---
## Development
Run tests:
```bash
pytest -q
```

Lint (optional if you add ruff):
```bash
ruff check .
```

---
## Architecture Overview
```
reelctxt/
  cli.py              # argparse entrypoint
  ingestion/
    __init__.py
    text_loader.py    # load & clean text from files & URLs
    crawler.py        # simple same-domain crawler
    image_loader.py   # gather image paths + basic features
  llm/
    __init__.py
    client.py         # generic LLM wrapper
    prompts.py        # prompt templates
  planning/
    __init__.py
    summarizer.py     # condense corpus
    storyboard.py     # build segment list
    selector.py       # match images to beats
  media/
    __init__.py
    tts.py            # narration synthesis abstraction
    compose.py        # ffmpeg composition
    kenburns.py       # pan/zoom utilities
  util/
    __init__.py
    logging.py
    timing.py
```

---
## Disclaimer
This is an educational scaffold. You must supply / configure your own model + TTS providers and ensure license compliance for ingested content.
