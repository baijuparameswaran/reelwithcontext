from __future__ import annotations
import argparse
from pathlib import Path
from .util.logging import setup_logging
from .ingestion.text_loader import load_text_from_files, fetch_url
from .ingestion.crawler import crawl
from .ingestion.image_loader import load_images
from .llm.client import LLMClient
from .planning.summarizer import build_summary
from .planning.storyboard import build_storyboard
from .planning.selector import select_images_for_segments
from .planning.segment import validate_segments
from .media.tts import synthesize_segments
from .media.compose import build_timeline, create_video


def parse_args():
    p = argparse.ArgumentParser(description="Generate a reel video from prompt + context")
    p.add_argument('--prompt', required=True)
    p.add_argument('--text-folder', help='Folder with text files')
    p.add_argument('--image-folder', help='Folder with images')
    p.add_argument('--url', action='append', help='Seed URL(s) to crawl (same domain)')
    p.add_argument('--crawl-depth', type=int, default=0)
    p.add_argument('--segments', type=int, default=6)
    p.add_argument('--output', default='reel.mp4')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--log-level', default='INFO')
    p.add_argument('--music', help='Optional background music audio file (loops/trimmed)')
    p.add_argument('--music-intro', help='Optional intro music stem (plays at start, auto-fade)')
    p.add_argument('--music-outro', help='Optional outro music stem (fades in near end)')
    p.add_argument('--music-volume', type=float, default=0.20, help='Linear volume factor for music (default 0.20)')
    p.add_argument('--no-duck', action='store_true', help='Disable sidechain ducking (music will just mix)')
    p.add_argument('--no-captions', action='store_true', help='Disable caption overlays')
    p.add_argument('--caption-mode', choices=['title','narration'], default='title', help='Caption text source')
    p.add_argument('--caption-font', help='Path to a .ttf font file for drawtext')
    p.add_argument('--caption-color', default='white')
    p.add_argument('--caption-box-color', default='black@0.5')
    p.add_argument('--caption-max-chars', type=int, default=80)
    p.add_argument('--ken-burns', action='store_true', help='Enable Ken Burns slow zoom on still images')
    p.add_argument('--ken-burns-zoom', type=float, default=1.08, help='Final zoom factor for Ken Burns (default 1.08)')
    p.add_argument('--no-continuous-music', action='store_true', help='Disable continuous music bed (loop per segment instead)')
    p.add_argument('--fade-in', type=float, default=1.5, help='Music fade-in duration (continuous mode)')
    p.add_argument('--fade-out', type=float, default=1.5, help='Music fade-out duration (continuous mode)')
    p.add_argument('--no-voice-normalize', action='store_true', help='Disable loudness normalization on narration track')
    p.add_argument('--keep-temp', action='store_true', help='Keep temporary build directory and intermediate files')
    p.add_argument('--pre-cleanup', action='store_true', help='Remove previous temp directory before starting')
    return p.parse_args()


def main():
    args = parse_args()
    setup_logging(args.log_level)

    # Ingest text
    corpus = []
    if args.text_folder:
        corpus.extend(load_text_from_files(args.text_folder))
    if args.url:
        for u in args.url:
            if args.crawl_depth > 0:
                pages = crawl(u, max_depth=args.crawl_depth)
                for p in pages:
                    corpus.append({'path': p.url, 'content': p.text})
            else:
                txt = fetch_url(u)
                if txt:
                    corpus.append({'path': u, 'content': txt})
    corpus_texts = [c['content'] for c in corpus]

    # Images
    images = []
    if args.image_folder:
        images = load_images(args.image_folder)

    llm = LLMClient()
    summary = build_summary(args.prompt, corpus_texts, llm) if corpus_texts else args.prompt
    segments = build_storyboard(args.prompt, summary, args.segments, llm)

    select_images_for_segments(segments, images, corpus_texts or [summary])
    # Validation (images optional)
    validate_segments(segments, require_images=False)

    if args.dry_run:
        from pprint import pprint
        pprint(segments)
        return

    build_timeline(segments)
    audio_paths = synthesize_segments(segments, out_dir=Path('audio_cache'))
    create_video(
        segments,
        audio_paths,
        args.output,
        music_path=args.music,
    music_intro_path=args.music_intro,
    music_outro_path=args.music_outro,
        music_volume=args.music_volume,
        duck=not args.no_duck,
        captions=not args.no_captions,
        caption_mode=args.caption_mode,
        caption_max_chars=args.caption_max_chars,
        caption_color=args.caption_color,
        caption_box=True,
        caption_box_color=args.caption_box_color,
        caption_font=args.caption_font,
        ken_burns=args.ken_burns,
        ken_burns_zoom=args.ken_burns_zoom,
        continuous_music=not args.no_continuous_music,
        fade_in=args.fade_in,
        fade_out=args.fade_out,
        normalize_voice=not args.no_voice_normalize,
        keep_temp=args.keep_temp,
        pre_cleanup=args.pre_cleanup,
    )
    print(f"Created {args.output}")

if __name__ == '__main__':
    main()
