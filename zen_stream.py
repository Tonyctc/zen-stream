#!/usr/bin/env python3
"""
Zen Stream — Fully Automated Pipeline
Generates zen meditation videos with procedural audio + fractal backgrounds.

Usage:
    python3 zen_stream.py                          # 10s test
    python3 zen_stream.py -d 3600 -r 720p         # 1 hour, 720p
    python3 zen_stream.py --preset zen             # preset "zen"
    python3 zen_stream.py --batch presets.json     # batch from config
    python3 zen_stream.py --loop                   # generate forever
    python3 zen_stream.py --loop --upload          # generate + upload to YouTube
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time as _time
from datetime import datetime


# ─── Presets ──────────────────────────────────────────────────────────

PRESETS = {
    'zen': {
        'type': 'julia', 'palette': 'zen', 'mode': 'meditation',
        'resolution': '720p', 'iterations': 80, 'fps': 24, 'duration': 3600,
        'title': 'Zen Meditation — Fractal Ambient Music',
        'description': 'Relaxing zen meditation with ambient music and animated fractal art. Perfect for yoga, meditation, study, and sleep.',
        'tags': 'zen,meditation,ambient,fractal,relaxation,music,sleep,study,yoga',
    },
    'sleep': {
        'type': 'plasma', 'palette': 'ocean', 'mode': 'sleep',
        'resolution': '480p', 'iterations': 60, 'fps': 24, 'duration': 28800,
        'title': 'Deep Sleep — 8 Hours Ocean Ambient',
        'description': '8 hours of calming ocean-inspired visuals with soothing ambient sounds for deep sleep.',
        'tags': 'sleep,insomnia,8hours,ocean,ambient,relaxation,asmr',
    },
    'focus': {
        'type': 'mandelbrot', 'palette': 'ember', 'mode': 'focus',
        'resolution': '720p', 'iterations': 100, 'fps': 24, 'duration': 7200,
        'title': 'Deep Focus — Fractal Ambient for Studying',
        'description': '2 hours of mesmerizing fractal visuals with focus-enhancing ambient music. Ideal for studying, coding, and deep work.',
        'tags': 'focus,study,concentration,ambient,fractal,lofi,coding',
    },
    'aurora': {
        'type': 'julia', 'palette': 'aurora', 'mode': 'meditation',
        'resolution': '1080p', 'iterations': 100, 'fps': 24, 'duration': 3600,
        'title': 'Aurora Borealis — Meditation Ambient',
        'description': '1 hour of aurora-inspired fractal visuals with ambient meditation music.',
        'tags': 'aurora,meditation,ambient,fractal,northern lights,relaxation',
    },
    'nature': {
        'type': 'plasma', 'palette': 'zen', 'mode': 'nature',
        'resolution': '720p', 'iterations': 60, 'fps': 24, 'duration': 3600,
        'title': 'Nature Sounds — Zen Garden Ambient',
        'description': '1 hour of nature-inspired ambient with water drops, wind, and gentle bells.',
        'tags': 'nature,sounds,zen,garden,water,wind,bells,ambient',
    },
}


# ─── Core Functions ──────────────────────────────────────────────────

def find_ffmpeg():
    """Find ffmpeg binary."""
    for path in ['ffmpeg', '/usr/bin/ffmpeg', '/usr/local/bin/ffmpeg',
                 '/opt/homebrew/bin/ffmpeg']:
        try:
            result = subprocess.run([path, '-version'], capture_output=True, timeout=5)
            if result.returncode == 0:
                return path
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    return None


def generate_one(config, output_dir, ffmpeg_path, keep_frames=False, upload=False):
    """Generate a single video from config dict."""
    t_type = config.get('type', 'julia')
    palette = config.get('palette', 'zen')
    mode = config.get('mode', 'meditation')
    resolution = config.get('resolution', '480p')
    iterations = config.get('iterations', 80)
    fps = config.get('fps', 24)
    duration = config.get('duration', 10)
    tuning = config.get('tuning', 432)
    title = config.get('title', 'Zen Stream')

    os.makedirs(output_dir, exist_ok=True)

    audio_file = os.path.join(output_dir, f'zen_{mode}.wav')
    frames_dir = os.path.join(output_dir, 'frames')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = os.path.join(output_dir, f'zen_{t_type}_{palette}_{timestamp}.mp4')

    t_start = _time.time()

    # ─── Step 1: Audio ────────────────────────────────────────
    print(f"\n{'#'*60}")
    print(f"  GENERATING: {title}")
    print(f"  Duration: {duration}s | Resolution: {resolution}")
    print(f"  Fractal: {t_type} | Palette: {palette} | Audio: {mode} ({tuning}Hz)")
    print(f"{'#'*60}")

    print(f"\n[1/3] Generating audio ({mode}, {tuning}Hz)...")
    from zen_audio import write_wav
    write_wav(audio_file, duration, mode, tuning)

    # ─── Step 2: Video ────────────────────────────────────────
    print(f"\n[2/3] Generating video frames...")
    from fractal_video import parse_resolution, RENDERERS, write_ppm_header, write_ppm_frame

    width, height = parse_resolution(resolution)
    total_frames = int(duration * fps)
    renderer = RENDERERS[t_type]

    os.makedirs(frames_dir, exist_ok=True)
    ft_start = _time.time()

    for frame in range(total_frames):
        pixels = renderer(width, height, frame, total_frames,
                          palette_name=palette, max_iter=iterations)
        fname = os.path.join(frames_dir, f'frame_{frame:06d}.ppm')
        with open(fname, 'wb') as f:
            write_ppm_header(f, width, height)
            write_ppm_frame(f, pixels)

        if frame % (fps * 5) == 0 or frame == total_frames - 1:
            elapsed = _time.time() - ft_start
            fps_actual = (frame + 1) / elapsed if elapsed > 0 else 0
            eta = (total_frames - frame - 1) / fps_actual if fps_actual > 0 else 0
            pct = (frame + 1) * 100 // total_frames
            print(f"  [{pct:3d}%] {frame+1}/{total_frames} frames | "
                  f"{fps_actual:.1f} fps | ETA: {eta:.0f}s", flush=True)

    print(f"  Frames done in {_time.time() - ft_start:.1f}s")

    # ─── Step 3: Compose ──────────────────────────────────────
    print(f"\n[3/3] Composing final video...")

    if not ffmpeg_path:
        print("  ffmpeg NOT FOUND — skipping composition")
        print(f"  Frames: {frames_dir}/")
        print(f"  Audio:  {audio_file}")
        success = False
    else:
        frames_pattern = os.path.join(frames_dir, 'frame_%06d.ppm')
        cmd = [
            ffmpeg_path, '-y',
            '-framerate', str(fps),
            '-i', frames_pattern,
            '-i', audio_file,
            '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac', '-b:a', '128k',
            '-shortest',
            output_file
        ]
        result = subprocess.run(cmd, capture_output=True)
        success = result.returncode == 0

        if success:
            size_mb = os.path.getsize(output_file) / (1024 * 1024)
            print(f"  Output: {output_file} ({size_mb:.1f} MB)")
        else:
            print(f"  ffmpeg error (code {result.returncode})")

    # Cleanup frames
    if success and not keep_frames:
        shutil.rmtree(frames_dir, ignore_errors=True)

    elapsed = _time.time() - t_start
    print(f"\n{'─'*60}")
    print(f"  DONE in {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"  File: {output_file if success else '(composition failed)'}")
    print(f"{'─'*60}")

    # ─── Upload ───────────────────────────────────────────────
    if success and upload:
        upload_to_youtube(output_file, config)

    return output_file if success else None


def upload_to_youtube(video_path, config):
    """Upload video to YouTube using the API."""
    uploader = os.path.join(os.path.dirname(__file__), 'upload_youtube.py')
    if not os.path.exists(uploader):
        print("\n  Upload script not found. Creating it now...")
        return False

    title = config.get('title', 'Zen Stream')
    description = config.get('description', '')
    tags = config.get('tags', 'zen,meditation,ambient')

    cmd = [
        sys.executable, uploader,
        '--file', video_path,
        '--title', title,
        '--description', description,
        '--tags', tags,
        '--category', '10',  # Music
        '--privacy', 'public',
    ]

    print(f"\n  Uploading to YouTube: {title}...")
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode == 0


# ─── Batch Mode ──────────────────────────────────────────────────────

def run_batch(config_file, output_dir, ffmpeg_path, keep_frames=False, upload=False):
    """Run batch generation from JSON config file."""
    with open(config_file, 'r') as f:
        config = json.load(f)

    if isinstance(config, list):
        jobs = config
    elif isinstance(config, dict) and 'jobs' in config:
        jobs = config['jobs']
    else:
        jobs = [config]

    total = len(jobs)
    print(f"\n{'='*60}")
    print(f"  BATCH MODE: {total} videos to generate")
    print(f"{'='*60}")

    results = []
    for i, job in enumerate(jobs):
        # Allow preset references
        if 'preset' in job:
            preset = PRESETS.get(job['preset'], {})
            job = {**preset, **{k: v for k, v in job.items() if k != 'preset'}}

        job_dir = os.path.join(output_dir, f'job_{i+1:03d}')
        print(f"\n{'━'*60}")
        print(f"  JOB {i+1}/{total}")
        print(f"{'━'*60}")

        result = generate_one(job, job_dir, ffmpeg_path, keep_frames, upload)
        results.append(result)

    # Summary
    success = sum(1 for r in results if r)
    print(f"\n{'='*60}")
    print(f"  BATCH COMPLETE: {success}/{total} videos generated")
    print(f"  Output: {output_dir}/")
    print(f"{'='*60}")

    return results


# ─── Loop Mode ───────────────────────────────────────────────────────

def run_loop(output_dir, ffmpeg_path, preset='zen', upload=False, interval=0):
    """Generate videos in an infinite loop."""
    config = PRESETS.get(preset, PRESETS['zen'])

    cycle = 0
    print(f"\n{'='*60}")
    print(f"  LOOP MODE — Generating videos forever")
    print(f"  Preset: {preset}")
    print(f"  Press Ctrl+C to stop")
    print(f"{'='*60}")

    while True:
        cycle += 1
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        job_dir = os.path.join(output_dir, f'cycle_{cycle:04d}_{timestamp}')

        print(f"\n{'━'*60}")
        print(f"  CYCLE {cycle} — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'━'*60}")

        result = generate_one(config, job_dir, ffmpeg_path,
                              keep_frames=False, upload=upload)

        if interval > 0:
            print(f"\n  Waiting {interval}s before next cycle...")
            _time.sleep(interval)

        print(f"\n  Cycle {cycle} complete. Starting next...")


# ─── Sample Config Generator ─────────────────────────────────────────

def generate_sample_config(output_file='presets.json'):
    """Generate a sample batch config file."""
    sample = {
        "description": "Zen Stream batch config — edit to customize",
        "jobs": [
            {"preset": "zen"},
            {"preset": "sleep"},
            {"preset": "focus"},
            {
                "type": "julia",
                "palette": "aurora",
                "mode": "meditation",
                "resolution": "720p",
                "duration": 1800,
                "title": "Custom Aurora Video",
                "tags": "aurora,meditation,custom",
            },
        ]
    }

    with open(output_file, 'w') as f:
        json.dump(sample, f, indent=2, ensure_ascii=False)

    print(f"Sample config saved: {output_file}")
    print(f"Edit it and run: python3 zen_stream.py --batch {output_file}")


# ─── CLI ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Zen Stream — Automated Zen Video Generator',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Presets available:
{chr(10).join(f'  {k:12s} {v["title"]}' for k, v in PRESETS.items())}

Examples:
  python3 zen_stream.py --preset zen             # Generate 1h zen video
  python3 zen_stream.py --preset sleep           # Generate 8h sleep video
  python3 zen_stream.py --batch presets.json     # Batch from config
  python3 zen_stream.py --loop --preset zen      # Generate forever
  python3 zen_stream.py --loop --upload          # Generate + upload forever
  python3 zen_stream.py --sample-config          # Create sample presets.json
        """,
    )

    # Main mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--batch', type=str, metavar='CONFIG',
                            help='Batch mode: generate from JSON config')
    mode_group.add_argument('--loop', action='store_true',
                            help='Loop mode: generate videos forever')
    mode_group.add_argument('--sample-config', action='store_true',
                            help='Generate a sample presets.json')

    # Preset / manual
    parser.add_argument('--preset', type=str, choices=list(PRESETS.keys()),
                        help='Use a predefined preset')
    parser.add_argument('-d', '--duration', type=float, default=None,
                        help='Override duration (seconds)')
    parser.add_argument('-r', '--resolution', type=str, default=None,
                        help='Override resolution')
    parser.add_argument('-t', '--type', type=str, default=None,
                        choices=['mandelbrot', 'julia', 'plasma'])
    parser.add_argument('-p', '--palette', type=str, default=None,
                        choices=['zen', 'aurora', 'ember', 'ocean'])
    parser.add_argument('-m', '--mode', type=str, default=None,
                        choices=['meditation', 'sleep', 'focus', 'nature'])
    parser.add_argument('-i', '--iterations', type=int, default=None)
    parser.add_argument('-f', '--fps', type=int, default=None)
    parser.add_argument('--tuning', type=float, default=432,
                        help='Base tuning frequency in Hz (default: 432)')

    # Output
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='Output MP4 file (single mode)')
    parser.add_argument('--output-dir', type=str, default='output',
                        help='Output directory')

    # Actions
    parser.add_argument('--upload', action='store_true',
                        help='Upload to YouTube after generation')
    parser.add_argument('--keep-frames', action='store_true',
                        help='Keep intermediate PPM frames')
    parser.add_argument('--audio-only', action='store_true',
                        help='Generate audio only')
    parser.add_argument('--video-only', action='store_true',
                        help='Generate video only')

    args = parser.parse_args()

    # ─── Sample Config ────────────────────────────────────────
    if args.sample_config:
        generate_sample_config()
        return

    ffmpeg = find_ffmpeg()

    # ─── Batch Mode ───────────────────────────────────────────
    if args.batch:
        run_batch(args.batch, args.output_dir, ffmpeg,
                  keep_frames=args.keep_frames, upload=args.upload)
        return

    # ─── Loop Mode ────────────────────────────────────────────
    if args.loop:
        preset = args.preset or 'zen'
        run_loop(args.output_dir, ffmpeg, preset=preset,
                 upload=args.upload)
        return

    # ─── Single Mode ──────────────────────────────────────────
    # Start from preset or defaults
    if args.preset:
        config = dict(PRESETS[args.preset])
    else:
        config = {
            'type': 'julia', 'palette': 'zen', 'mode': 'meditation',
            'resolution': '480p', 'iterations': 80, 'fps': 24, 'duration': 10,
            'title': 'Zen Stream Test',
            'tags': 'zen,ambient,test',
        }

    # Apply overrides
    if args.duration is not None:
        config['duration'] = args.duration
    if args.resolution is not None:
        config['resolution'] = args.resolution
    if args.type is not None:
        config['type'] = args.type
    if args.palette is not None:
        config['palette'] = args.palette
    if args.mode is not None:
        config['mode'] = args.mode
    if args.iterations is not None:
        config['iterations'] = args.iterations
    if args.fps is not None:
        config['fps'] = args.fps
    config['tuning'] = args.tuning

    # Audio-only mode
    if args.audio_only:
        os.makedirs(args.output_dir, exist_ok=True)
        audio_file = os.path.join(args.output_dir, f'zen_{config["mode"]}.wav')
        from zen_audio import write_wav
        write_wav(audio_file, config['duration'], config['mode'], config.get('tuning', 432))
        return

    # Video-only mode
    if args.video_only:
        config['_video_only'] = True

    output = generate_one(config, args.output_dir, ffmpeg,
                           keep_frames=args.keep_frames, upload=args.upload)


if __name__ == '__main__':
    main()
