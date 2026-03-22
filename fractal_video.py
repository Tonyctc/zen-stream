#!/usr/bin/env python3
"""
Fractal Video Generator — Procedural zen fractal animations.
Pure Python, zero dependencies.

Renders Mandelbrot/Julia fractal zoom sequences as PPM frames.
Designed to create seamless loops for YouTube meditation channels.

Usage:
    python3 fractal_video.py                    # 10s test at low res
    python3 fractal_video.py -d 60 -r 720p     # 1 minute, 720p
    python3 fractal_video.py --pipe | ffmpeg ... # pipe to ffmpeg
"""

import math
import struct
import argparse
import sys
import os
import time as _time


# ─── Color Palettes (zen-themed) ─────────────────────────────────────

PALETTES = {
    'zen': [
        (15, 25, 45),     # deep navy
        (30, 60, 90),     # ocean blue
        (60, 120, 140),   # teal
        (100, 170, 160),  # seafoam
        (150, 200, 180),  # sage
        (200, 220, 200),  # pale mint
        (240, 240, 230),  # cream highlight
    ],
    'aurora': [
        (10, 5, 30),      # deep purple
        (40, 10, 80),     # violet
        (80, 20, 120),    # magenta
        (120, 50, 150),   # orchid
        (60, 120, 180),   # blue
        (40, 180, 150),   # cyan
        (100, 220, 100),  # green
        (200, 240, 150),  # lime glow
    ],
    'ember': [
        (20, 5, 5),       # dark red
        (60, 15, 10),     # crimson
        (120, 30, 15),    # rust
        (180, 60, 20),    # orange
        (220, 120, 30),   # gold
        (240, 180, 60),   # yellow
        (250, 220, 120),  # cream
    ],
    'ocean': [
        (5, 10, 30),      # midnight
        (10, 30, 70),     # deep blue
        (20, 60, 120),    # ocean
        (40, 100, 160),   # mid blue
        (60, 150, 190),   # light blue
        (100, 190, 210),  # sky
        (160, 220, 235),  # foam
        (220, 240, 250),  # white cap
    ],
}


def lerp_color(c1, c2, t):
    """Linear interpolation between two RGB tuples."""
    return (
        int(c1[0] + (c2[0] - c1[0]) * t),
        int(c1[1] + (c2[1] - c1[1]) * t),
        int(c1[2] + (c2[2] - c1[2]) * t),
    )


def palette_lookup(palette, t):
    """Map a normalized value [0,1] to a color from the palette."""
    if t <= 0:
        return palette[0]
    if t >= 1:
        return palette[-1]
    scaled = t * (len(palette) - 1)
    idx = int(scaled)
    frac = scaled - idx
    if idx >= len(palette) - 1:
        return palette[-1]
    return lerp_color(palette[idx], palette[idx + 1], frac)


# ─── Mandelbrot / Julia Computation ──────────────────────────────────

def mandelbrot_pixel(cx, cy, max_iter):
    """Compute Mandelbrot iteration count for point (cx, cy)."""
    x = 0.0
    y = 0.0
    xx = 0.0
    yy = 0.0
    for i in range(max_iter):
        if xx + yy > 4.0:
            # Smooth coloring
            log_zn = math.log(xx + yy) / 2.0
            nu = math.log(log_zn / math.log(2)) / math.log(2)
            return i + 1 - nu
        y = 2 * x * y + cy
        x = xx - yy + cx
        xx = x * x
        yy = y * y
    return max_iter


def julia_pixel(cx, cy, jr, ji, max_iter):
    """Compute Julia iteration count for point (cx, cy) with constant (jr, ji)."""
    x = cx
    y = cy
    xx = x * x
    yy = y * y
    for i in range(max_iter):
        if xx + yy > 4.0:
            log_zn = math.log(xx + yy) / 2.0
            nu = math.log(log_zn / math.log(2)) / math.log(2)
            return i + 1 - nu
        y = 2 * x * y + ji
        x = xx - yy + jr
        xx = x * x
        yy = y * y
    return max_iter


def burning_ship_pixel(cx, cy, max_iter):
    """Compute Burning Ship iteration count."""
    x = 0.0
    y = 0.0
    xx = 0.0
    yy = 0.0
    for i in range(max_iter):
        if xx + yy > 4.0:
            log_zn = math.log(xx + yy) / 2.0
            nu = math.log(log_zn / math.log(2)) / math.log(2)
            return i + 1 - nu
        y = abs(2 * x * y) + cy
        x = xx - yy + cx
        xx = x * x
        yy = y * y
    return max_iter


# ─── Frame Renderers ─────────────────────────────────────────────────

def render_mandelbrot_zoom(width, height, frame_idx, total_frames, palette_name='zen',
                           max_iter=128, **_kw):
    """Render a single frame of a Mandelbrot zoom sequence."""
    palette = PALETTES[palette_name]

    center_x = -0.75
    center_y = 0.0
    zoom_start = 1.0
    zoom_end = 1000.0

    # Logarithmic zoom interpolation for smooth feel
    t = frame_idx / total_frames
    zoom = zoom_start * (zoom_end / zoom_start) ** t

    aspect = width / height
    scale = 2.5 / zoom

    x_min = center_x - scale * aspect
    x_max = center_x + scale * aspect
    y_min = center_y - scale
    y_max = center_y + scale

    pixels = []
    inv_w = 1.0 / (width - 1) if width > 1 else 1.0
    inv_h = 1.0 / (height - 1) if height > 1 else 1.0
    inv_iter = 1.0 / max_iter

    for py in range(height):
        cy = y_min + (y_max - y_min) * py * inv_h
        for px in range(width):
            cx = x_min + (x_max - x_min) * px * inv_w
            n = mandelbrot_pixel(cx, cy, max_iter)
            if n >= max_iter:
                pixels.append(palette[0])
            else:
                t_color = (n * inv_iter) % 1.0
                pixels.append(palette_lookup(palette, t_color))

    return pixels


def render_julia_animated(width, height, frame_idx, total_frames, palette_name='aurora',
                          max_iter=128, **_kw):
    """Render a frame of an animated Julia set."""
    palette = PALETTES[palette_name]

    t = frame_idx / total_frames

    # Animate the Julia constant along a rose curve path that loops
    angle = 2 * math.pi * t
    r = 0.7885 * (1 + 0.5 * math.cos(5 * angle))
    jr = r * math.cos(angle)
    ji = r * math.sin(angle)

    scale = 2.0
    aspect = width / height
    x_min, x_max = -scale * aspect, scale * aspect
    y_min, y_max = -scale, scale

    pixels = []
    inv_w = 1.0 / (width - 1) if width > 1 else 1.0
    inv_h = 1.0 / (height - 1) if height > 1 else 1.0
    inv_iter = 1.0 / max_iter

    for py in range(height):
        cy = y_min + (y_max - y_min) * py * inv_h
        for px in range(width):
            cx = x_min + (x_max - x_min) * px * inv_w
            n = julia_pixel(cx, cy, jr, ji, max_iter)
            if n >= max_iter:
                pixels.append(palette[0])
            else:
                t_color = (n * inv_iter * 2) % 1.0
                pixels.append(palette_lookup(palette, t_color))

    return pixels


def render_plasma(width, height, frame_idx, total_frames, palette_name='ocean',
                  speed=1.0, **_kw):
    """Render a plasma/fractal noise frame (fast, smooth, always loops)."""
    palette = PALETTES[palette_name]
    t = frame_idx / total_frames * 2 * math.pi * speed

    pixels = []
    w_inv = 1.0 / width
    h_inv = 1.0 / height

    for py in range(height):
        y = py * h_inv
        for px in range(width):
            x = px * w_inv

            # Multi-frequency plasma
            v1 = math.sin(x * 10.0 + t)
            v2 = math.sin(10.0 * (x * math.sin(t / 2.0) + y * math.cos(t / 3.0)) + t)
            cx = x + 0.5 * math.sin(t / 5.0)
            cy = y + 0.5 * math.cos(t / 3.0)
            v3 = math.sin(math.sqrt(100.0 * (cx * cx + cy * cy) + 1.0) + t)
            v4 = math.sin(math.sqrt(100.0 * ((x - 0.5) ** 2 + (y - 0.5) ** 2) + 1.0) - t)

            v = (v1 + v2 + v3 + v4) * 0.25
            v = (v + 1.0) * 0.5  # normalize to [0, 1]

            pixels.append(palette_lookup(palette, v))

    return pixels


# ─── PPM Output ──────────────────────────────────────────────────────

def write_ppm_header(f, width, height):
    """Write PPM binary header."""
    f.write(f'P6\n{width} {height}\n255\n'.encode())


def pixels_to_bytes(pixels):
    """Convert list of (r,g,b) tuples to bytes."""
    parts = []
    for r, g, b in pixels:
        parts.append(bytes([max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))]))
    return b''.join(parts)


def write_ppm_frame(f, pixels):
    """Write a single PPM frame (without header)."""
    f.write(pixels_to_bytes(pixels))


# ─── Resolution Presets ──────────────────────────────────────────────

RESOLUTIONS = {
    '480p': (854, 480),
    '720p': (1280, 720),
    '1080p': (1920, 1080),
    '360p': (640, 360),
    '240p': (426, 240),
}


def parse_resolution(res_str):
    """Parse resolution string like '720p' or '1280x720'."""
    if res_str in RESOLUTIONS:
        return RESOLUTIONS[res_str]
    if 'x' in res_str:
        w, h = res_str.split('x')
        return int(w), int(h)
    raise ValueError(f"Unknown resolution: {res_str}")


# ─── Main ────────────────────────────────────────────────────────────

RENDERERS = {
    'mandelbrot': render_mandelbrot_zoom,
    'julia': render_julia_animated,
    'plasma': render_plasma,
}


def main():
    parser = argparse.ArgumentParser(description='Fractal Video Generator')
    parser.add_argument('-d', '--duration', type=float, default=10,
                        help='Duration in seconds (default: 10)')
    parser.add_argument('-f', '--fps', type=int, default=24,
                        help='Frames per second (default: 24)')
    parser.add_argument('-r', '--resolution', type=str, default='480p',
                        help='Resolution: 240p/360p/480p/720p/1080p or WxH')
    parser.add_argument('-t', '--type', type=str, default='julia',
                        choices=['mandelbrot', 'julia', 'plasma'],
                        help='Fractal type (default: julia)')
    parser.add_argument('-p', '--palette', type=str, default='zen',
                        choices=list(PALETTES.keys()),
                        help='Color palette (default: zen)')
    parser.add_argument('-i', '--iterations', type=int, default=100,
                        help='Max iterations (default: 100)')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='Output directory for PPM frames')
    parser.add_argument('--pipe', action='store_true',
                        help='Pipe PPM frames to stdout (for ffmpeg)')
    parser.add_argument('--preview', type=int, default=None,
                        help='Generate a single preview frame (frame number)')
    args = parser.parse_args()

    width, height = parse_resolution(args.resolution)
    fps = args.fps
    total_frames = int(args.duration * fps)
    renderer = RENDERERS[args.type]

    if args.preview is not None:
        # Single frame preview
        fname = f'preview_{args.type}_{args.palette}.ppm'
        print(f"Rendering preview frame {args.preview} ({width}x{height})...")
        pixels = renderer(width, height, args.preview, max(total_frames, 1),
                          palette_name=args.palette, max_iter=args.iterations)
        with open(fname, 'wb') as f:
            write_ppm_header(f, width, height)
            write_ppm_frame(f, pixels)
        print(f"Saved: {fname}")
        return

    if args.pipe:
        # Pipe mode: write raw PPM stream to stdout
        out = sys.stdout.buffer
        for frame in range(total_frames):
            pixels = renderer(width, height, frame, total_frames,
                              palette_name=args.palette, max_iter=args.iterations)
            write_ppm_header(out, width, height)
            write_ppm_frame(out, pixels)
            if frame % fps == 0:
                print(f"Frame {frame}/{total_frames}", file=sys.stderr, flush=True)
        return

    # File output mode
    out_dir = args.output or f'frames_{args.type}_{args.palette}'
    os.makedirs(out_dir, exist_ok=True)

    print(f"Rendering {total_frames} frames ({args.duration}s @ {fps}fps)")
    print(f"Resolution: {width}x{height}")
    print(f"Fractal: {args.type}, Palette: {args.palette}")
    print(f"Output: {out_dir}/")

    t_start = _time.time()

    for frame in range(total_frames):
        pixels = renderer(width, height, frame, total_frames,
                          palette_name=args.palette, max_iter=args.iterations)
        fname = os.path.join(out_dir, f'frame_{frame:06d}.ppm')
        with open(fname, 'wb') as f:
            write_ppm_header(f, width, height)
            write_ppm_frame(f, pixels)

        if frame % fps == 0 or frame == total_frames - 1:
            elapsed = _time.time() - t_start
            fps_actual = (frame + 1) / elapsed if elapsed > 0 else 0
            eta = (total_frames - frame - 1) / fps_actual if fps_actual > 0 else 0
            print(f"  [{frame+1:5d}/{total_frames}] {fps_actual:.1f} fps, ETA: {eta:.0f}s",
                  flush=True)

    elapsed = _time.time() - t_start
    print(f"\nDone! {total_frames} frames in {elapsed:.1f}s")
    print(f"\nTo create video with ffmpeg:")
    print(f"  ffmpeg -framerate {fps} -i {out_dir}/frame_%06d.ppm "
          f"-c:v libx264 -pix_fmt yuv420p -preset medium fractal.mp4")


if __name__ == '__main__':
    main()
