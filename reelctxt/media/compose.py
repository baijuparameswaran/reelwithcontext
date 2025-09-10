from __future__ import annotations
import json
from pathlib import Path
import shutil
from typing import List, Optional
from ..planning.segment import Segment
import subprocess
import shlex
import math

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
SEG_DURATION = 3.5  # seconds baseline; could scale with narration length


def estimate_segment_duration(narration: str) -> float:
    wpm = 155.0
    words = len(narration.split())
    return max(2.0, min(8.0, words / wpm * 60.0))


def build_timeline(segments: List[Segment]):
    t = 0.0
    for seg in segments:
        d = estimate_segment_duration(seg.narration)
        seg.start = t
        seg.duration = d
        t += d


def create_video(
    segments: List[Segment],
    audio_paths: List[str],
    output_path: str,
    music_path: Optional[str] = None,
    music_intro_path: Optional[str] = None,
    music_outro_path: Optional[str] = None,
    music_volume: float = 0.20,
    duck: bool = True,
    captions: bool = True,
    caption_mode: str = "title",  # or 'narration'
    caption_max_chars: int = 80,
    caption_color: str = "white",
    caption_box: bool = True,
    caption_box_color: str = "black@0.5",
    caption_font: Optional[str] = None,
    ken_burns: bool = False,
    ken_burns_zoom: float = 1.08,
    continuous_music: bool = True,
    fade_in: float = 1.5,
    fade_out: float = 1.5,
    normalize_voice: bool = True,
    keep_temp: bool = False,
    pre_cleanup: bool = False,
):
    """Create final video.

    Parameters:
      segments: list of segment dicts (must have 'image','duration')
      audio_paths: narration wav paths aligned to segments
      output_path: final mp4 path
      music_path: optional background music file
      music_volume: linear volume factor applied to music before mix/duck
      duck: if True and music present, apply sidechain compression to dynamically duck music under narration
    """
    tmp_dir = Path(".reel_tmp")
    if pre_cleanup and tmp_dir.exists():
        shutil.rmtree(tmp_dir, ignore_errors=True)
    tmp_dir.mkdir(exist_ok=True)
    part_files: List[str] = []

    def escape_drawtext(text: str) -> str:
        # Escape characters for ffmpeg drawtext
        return text.replace('\\', '\\\\').replace(':', '\\:').replace("'", "\\'")

    for i, seg in enumerate(segments):
        img = seg.image
        dur = seg.duration
        base_chain = []
        if img:
            base_chain.append(f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=cover")
            if ken_burns:
                frames = int(dur * 30)
                # gradual zoom up to specified zoom factor; ensure <= zoom
                kb = f"zoompan=z='min(1+0.0005*in,{ken_burns_zoom})':d={frames}:fps=30"
                base_chain.append(kb)
        else:
            # Generate color background; use alternating palette for variety
            colors = ["0x222222", "0x2d1f44", "0x123a2a", "0x443311"]
            color = colors[i % len(colors)]
            # Use color source as input 0 instead of image file
            # We'll build a separate ffmpeg invocation (no -loop -i) using -f lavfi
        caption_filter = ""
        if captions:
            text_src = seg.title if caption_mode == 'title' else seg.narration
            if not text_src:
                text_src = seg.narration
            txt = text_src.strip().replace('\n', ' ')
            if len(txt) > caption_max_chars:
                txt = txt[:caption_max_chars-1] + '…'
            txt = escape_drawtext(txt)
            draw = [
                "drawtext=text='%s'" % txt,
                f":x=(w-text_w)/2:y=h-(text_h*2)-60",
                f":fontsize=52:fontcolor={caption_color}",
            ]
            if caption_font:
                draw.append(f":fontfile={escape_drawtext(caption_font)}")
            if caption_box:
                draw.append(f":box=1:boxcolor={caption_box_color}:boxborderw=20")
            caption_filter = ''.join(draw)
        if img:
            vf_chain = base_chain
            if caption_filter:
                vf_chain.append(caption_filter)
            vf = ','.join(vf_chain + ['format=yuv420p'])
        else:
            # Build filtergraph for color + captions
            color_filter = f"color=c={color}:size={VIDEO_WIDTH}x{VIDEO_HEIGHT}:d={dur:.2f}"
            if caption_filter:
                vf = f"{color_filter},{caption_filter},format=yuv420p"
            else:
                vf = f"{color_filter},format=yuv420p"
        part = tmp_dir / f"part_{i}.mp4"

        if music_path and not continuous_music:
            # Inputs: 0:v image, 1:a narration, 2:a music
            if duck:
                # Sidechain compress music using narration, then mix with narration
                fc = (
                    f"[2:a]aloop=loop=-1:size=2e9,volume={music_volume},atrim=0:{dur:.3f},asetpts=PTS-STARTPTS[music];"
                    f"[1:a]asetpts=PTS-STARTPTS[voice];"
                    f"[music][voice]sidechaincompress=threshold=0.1:ratio=8:attack=5:release=250:makeup=4[ducked];"
                    f"[ducked][voice]amix=inputs=2:dropout_transition=0:weights='1 1'[mixed]"
                )
                audio_map = '[mixed]'
            else:
                # Static attenuation + mix
                fc = (
                    f"[2:a]aloop=loop=-1:size=2e9,volume={music_volume},atrim=0:{dur:.3f},asetpts=PTS-STARTPTS[music];"
                    f"[1:a]asetpts=PTS-STARTPTS[voice];"
                    f"[music][voice]amix=inputs=2:dropout_transition=0:weights='1 1'[mixed]"
                )
                audio_map = '[mixed]'

            if img:
                cmd = [
                    'ffmpeg', '-y', '-loop', '1', '-i', img, '-i', audio_paths[i], '-i', music_path,
                    '-t', f"{dur:.2f}", '-filter_complex', fc,
                    '-map', '0:v', '-map', audio_map,
                    '-vf', vf,
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(part)
                ]
            else:
                # Color source replaces image input; supply narration + music only
                cmd = [
                    'ffmpeg', '-y', '-f', 'lavfi', '-i', f"color=c=black:size={VIDEO_WIDTH}x{VIDEO_HEIGHT}:d={dur:.2f}",
                    '-i', audio_paths[i], '-i', music_path,
                    '-t', f"{dur:.2f}", '-filter_complex', fc,
                    '-map', '0:v', '-map', audio_map,
                    '-vf', vf,
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-c:a', 'aac', str(part)
                ]
        else:
            if img:
                cmd = [
                    'ffmpeg', '-y', '-loop', '1', '-i', img,
                    '-i', audio_paths[i],
                    '-filter_complex', ('[1:a]loudnorm=I=-16:LRA=11:TP=-1.5[voice]' if normalize_voice else ''),
                    '-c:v', 'libx264', '-t', f"{dur:.2f}", '-pix_fmt', 'yuv420p',
                    '-vf', vf,
                    '-map', '0:v',
                    '-map', ('[voice]' if normalize_voice else '1:a'),
                    '-c:a', 'aac', '-shortest', str(part)
                ]
            else:
                cmd = [
                    'ffmpeg', '-y', '-f', 'lavfi', '-i', f"color=c=black:size={VIDEO_WIDTH}x{VIDEO_HEIGHT}:d={dur:.2f}",
                    '-i', audio_paths[i],
                    '-filter_complex', ('[1:a]loudnorm=I=-16:LRA=11:TP=-1.5[voice]' if normalize_voice else ''),
                    '-c:v', 'libx264', '-t', f"{dur:.2f}", '-pix_fmt', 'yuv420p',
                    '-vf', vf,
                    '-map', '0:v', '-map', ('[voice]' if normalize_voice else '1:a'),
                    '-c:a', 'aac', '-shortest', str(part)
                ]
        subprocess.run(cmd, check=True)
        part_files.append(str(part))

    # Concat parts
    concat_file = tmp_dir / 'list.txt'
    concat_file.write_text("\n".join(f"file '{p}'" for p in part_files))
    base_video = output_path if not (music_path and continuous_music) else str(Path(output_path).with_name(Path(output_path).stem + '_base.mp4'))
    cmd_concat = ['ffmpeg', '-y', '-f', 'concat', '-safe', '0', '-i', str(concat_file), '-c', 'copy', base_video]
    subprocess.run(cmd_concat, check=True)

    if (music_path or music_intro_path or music_outro_path) and continuous_music:
        total_duration = sum(s.duration for s in segments)
        # Clamp fades
        fade_in_eff = max(0.0, min(fade_in, total_duration/2))
        fade_out_eff = max(0.0, min(fade_out, total_duration/2))

        # Build command inputs: base video audio (voice), main bed (optional), intro, outro
        inputs = ['ffmpeg', '-y', '-i', base_video]
        music_input_indices = {}
        if music_path:
            music_input_indices['bed'] = len(inputs)//2  # after adding
            inputs += ['-i', music_path]
        if music_intro_path:
            music_input_indices['intro'] = (len(inputs)-1)
            inputs += ['-i', music_intro_path]
        if music_outro_path:
            music_input_indices['outro'] = (len(inputs)-1)
            inputs += ['-i', music_outro_path]

        filter_parts = []
        # Voice normalization
        if normalize_voice:
            filter_parts.append('[0:a]loudnorm=I=-16:LRA=11:TP=-1.5[voice]')
        else:
            filter_parts.append('[0:a]anull[voice]')

        music_tracks = []
        label_counter = 1
        stream_offset = 1
        def idx_to_label(i: int) -> str:
            return f'm{i}'

        next_input_idx = 1
        # Order: bed (loop trimmed), intro (fade out), outro (fade in with delay)
        if music_path:
            # bed is first additional input (index next_input_idx)
            bed_idx = next_input_idx
            next_input_idx += 1
            filter_parts.append(f'[{bed_idx}:a]aloop=loop=-1:size=2e9,atrim=0:{total_duration:.3f},asetpts=PTS-STARTPTS,volume={music_volume}' + (f',afade=t=in:st=0:d={fade_in_eff}' if fade_in_eff>0 else '') + (f',afade=t=out:st={max(0,total_duration-fade_out_eff):.3f}:d={fade_out_eff}' if fade_out_eff>0 else '') + '[bed]')
            music_tracks.append('[bed]')
        if music_intro_path:
            intro_idx = next_input_idx
            next_input_idx += 1
            # Determine intro duration? We'll just fade it out over its own natural end via afade out using 90% of fade_out_eff for short smoothing
            filter_parts.append(f'[{intro_idx}:a]asetpts=PTS-STARTPTS,volume={music_volume},afade=t=out:st={max(0,fade_in_eff-0.5):.3f}:d={min(2.0, fade_out_eff or 2.0)}[intro]')
            music_tracks.append('[intro]')
        if music_outro_path:
            outro_idx = next_input_idx
            next_input_idx += 1
            start_outro = max(0.0, total_duration - 5.0)  # assume 5s outro window
            filter_parts.append(f'[{outro_idx}:a]adelay={int(start_outro*1000)}|{int(start_outro*1000)},volume={music_volume},afade=t=in:st=0:d={min(2.0,fade_in_eff or 2.0)}[outro]')
            music_tracks.append('[outro]')

        if music_tracks:
            if len(music_tracks) == 1:
                filter_parts.append(f'{music_tracks[0]}anull[mus_mix]')
            else:
                filter_parts.append(''.join(music_tracks) + f'amix=inputs={len(music_tracks)}:normalize=0:dropout_transition=0[mus_mix]')
        else:
            # No music inputs, keep voice only
            filter_parts.append('[voice]anull[mixed_only_voice]')

        if music_tracks:
            if duck:
                filter_parts.append('[mus_mix][voice]sidechaincompress=threshold=0.1:ratio=8:attack=5:release=250:makeup=4[ducked]')
                filter_parts.append('[ducked][voice]amix=inputs=2:weights="1 1"[mixed]')
            else:
                filter_parts.append('[mus_mix][voice]amix=inputs=2:weights="1 1"[mixed]')
        else:
            filter_parts.append('[mixed_only_voice]anull[mixed]')

        filter_complex = ';'.join(filter_parts)
        final_cmd = [
            'ffmpeg', '-y',
            *inputs[1:],  # exclude initial 'ffmpeg' and '-y' duplicates
            '-filter_complex', filter_complex,
            '-map', '0:v', '-map', '[mixed]', '-c:v', 'copy', '-c:a', 'aac', output_path
        ]
        subprocess.run(final_cmd, check=True)

    # Cleanup
    if not keep_temp:
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            # remove base video if intermediate
            if base_video != output_path and Path(base_video).exists():
                Path(base_video).unlink()
        except Exception:
            pass

    # Save storyboard json
    meta_path = Path(output_path).with_suffix('.json')
    # Convert to JSON serializable structure
    serializable = [s.to_dict() for s in segments]
    meta_path.write_text(json.dumps(serializable, indent=2))
    return output_path
