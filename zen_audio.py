#!/usr/bin/env python3
"""
Zen Audio Generator — Procedural ambient/meditation audio.
Pure Python, zero dependencies.

Generates seamless WAV files with evolving pads, harmonics,
and nature-like textures.

Usage:
    python3 zen_audio.py                    # 1 hour, default settings
    python3 zen_audio.py -d 7200 -o zen.wav # 2 hours
    python3 zen_audio.py -m sleep -d 3600   # sleep mode
"""

import wave
import struct
import math
import random
import argparse
import sys
import os

SAMPLE_RATE = 44100
MAX_AMP = 32767


def clamp(val, lo=-1.0, hi=1.0):
    return max(lo, min(hi, val))


class SmoothNoise:
    """Perlin-like smooth noise generator."""

    def __init__(self, seed=None):
        self.rng = random.Random(seed)
        self.current = self.rng.uniform(-1, 1)
        self.target = self.rng.uniform(-1, 1)
        self.speed = 0.001

    def next(self):
        diff = self.target - self.current
        self.current += diff * self.speed
        if abs(diff) < 0.001:
            self.target = self.rng.uniform(-1, 1)
        return self.current


class Oscillator:
    """Sine wave oscillator with smooth frequency modulation."""

    def __init__(self, freq, sample_rate=SAMPLE_RATE):
        self.freq = freq
        self.phase = 0.0
        self.sample_rate = sample_rate
        self.freq_mod = SmoothNoise(seed=random.randint(0, 99999))
        self.freq_mod.speed = 0.0001

    def next(self):
        mod = self.freq_mod.next() * 0.5
        actual_freq = self.freq * (1.0 + mod * 0.01)
        self.phase += 2.0 * math.pi * actual_freq / self.sample_rate
        if self.phase > 2.0 * math.pi:
            self.phase -= 2.0 * math.pi
        return math.sin(self.phase)


class Envelope:
    """Slow amplitude envelope for pads."""

    def __init__(self, attack_s, sustain_s, release_s, sample_rate=SAMPLE_RATE):
        self.attack_samples = int(attack_s * sample_rate)
        self.sustain_samples = int(sustain_s * sample_rate)
        self.release_samples = int(release_s * sample_rate)
        self.total = self.attack_samples + self.sustain_samples + self.release_samples
        self.pos = 0

    def next(self):
        if self.pos < self.attack_samples:
            val = self.pos / self.attack_samples
        elif self.pos < self.attack_samples + self.sustain_samples:
            val = 1.0
        elif self.pos < self.total:
            remaining = self.total - self.pos
            val = remaining / self.release_samples
        else:
            val = 0.0
        self.pos += 1
        return val * val  # quadratic for smoothness


class ZenPad:
    """A layered pad voice with multiple oscillators."""

    def __init__(self, base_freq, harmonics, detune=0.002, seed=None):
        self.rng = random.Random(seed)
        self.oscillators = []
        for i, h_ratio in enumerate(harmonics):
            freq = base_freq * h_ratio
            if i > 0:
                freq *= 1.0 + self.rng.uniform(-detune, detune)
            osc = Oscillator(freq)
            self.oscillators.append((osc, 1.0 / (i + 1)))
        self.amp_mod = SmoothNoise(seed=seed)
        self.amp_mod.speed = 0.0003

    def next(self):
        amp = 0.5 + 0.5 * self.amp_mod.next()
        val = 0.0
        for osc, weight in self.oscillators:
            val += osc.next() * weight
        return clamp(val * amp * 0.3)


class NatureNoise:
    """Filtered noise for nature-like textures."""

    def __init__(self, seed=None, brightness=0.5):
        self.rng = random.Random(seed)
        self.brightness = brightness
        self.prev = 0.0
        self.lfo = SmoothNoise(seed=seed)
        self.lfo.speed = 0.0005

    def next(self):
        raw = self.rng.uniform(-1, 1)
        lfo_val = 0.3 + 0.7 * (0.5 + 0.5 * self.lfo.next())
        alpha = self.brightness * lfo_val * 0.3
        self.prev = self.prev * (1.0 - alpha) + raw * alpha
        return clamp(self.prev * 2.0)


class WindSound:
    """Simulated wind using filtered noise with slow modulation."""

    def __init__(self, seed=None):
        self.noise_gen = NatureNoise(seed=seed, brightness=0.3)
        self.vol_lfo = SmoothNoise(seed=seed)
        self.vol_lfo.speed = 0.0002
        self.bandpass_state = 0.0
        self.bandpass_state2 = 0.0

    def next(self):
        n = self.noise_gen.next()
        # Simple resonant filter
        self.bandpass_state = 0.97 * self.bandpass_state + 0.03 * n
        self.bandpass_state2 = 0.95 * self.bandpass_state2 + 0.05 * self.bandpass_state
        vol = 0.15 + 0.35 * (0.5 + 0.5 * self.vol_lfo.next())
        return clamp(self.bandpass_state2 * vol * 8.0)


class WaterDrops:
    """Occasional water drop sounds."""

    def __init__(self, seed=None, density=0.0003):
        self.rng = random.Random(seed)
        self.density = density
        self.drops = []

    def next(self):
        # Spawning
        if self.rng.random() < self.density:
            freq = self.rng.uniform(800, 2400)
            self.drops.append({
                'freq': freq,
                'phase': 0.0,
                'amp': self.rng.uniform(0.05, 0.15),
                'decay': self.rng.uniform(0.002, 0.008),
                'age': 0,
            })

        val = 0.0
        alive = []
        for d in self.drops:
            d['phase'] += 2.0 * math.pi * d['freq'] / SAMPLE_RATE
            env = math.exp(-d['age'] * d['decay'])
            val += math.sin(d['phase']) * d['amp'] * env
            d['age'] += 1
            if env > 0.001:
                alive.append(d)
        self.drops = alive
        return clamp(val)


class BellTone:
    """Occasional bell/chime tones (singing bowl style)."""

    def __init__(self, seed=None, density=0.00005):
        self.rng = random.Random(seed)
        self.density = density
        self.bells = []

    def next(self):
        if self.rng.random() < self.density:
            base = self.rng.choice([261.63, 329.63, 392.00, 440.00, 523.25])
            harmonics = [1.0, 2.0, 3.0, 5.2]
            self.bells.append({
                'partials': [(base * h, self.rng.uniform(0.3, 0.8)) for h in harmonics],
                'decay': self.rng.uniform(0.0003, 0.001),
                'age': 0,
                'amp': self.rng.uniform(0.08, 0.2),
            })

        val = 0.0
        alive = []
        for b in self.bells:
            env = math.exp(-b['age'] * b['decay'])
            sample = 0.0
            for freq, amp in b['partials']:
                phase = 2.0 * math.pi * freq * b['age'] / SAMPLE_RATE
                sample += math.sin(phase) * amp
            val += sample * b['amp'] * env
            b['age'] += 1
            if env > 0.001:
                alive.append(b)
        self.bells = alive
        return clamp(val * 0.5)


def generate_zen_audio(duration_sec, mode='meditation', sample_rate=SAMPLE_RATE):
    """
    Generate procedural zen audio.

    Yields samples (floats in [-1, 1]) one at a time.
    """
    rng = random.Random(42)

    # Scale frequencies based on mode
    if mode == 'meditation':
        # C major pentatonic spread across octaves
        freqs = [65.41, 130.81, 164.81, 196.00, 261.63, 329.63, 392.00]
        bell_density = 0.00005
        wind_vol = 0.3
        water_density = 0.0002
    elif mode == 'sleep':
        freqs = [55.00, 82.41, 110.00, 146.83, 164.81]
        bell_density = 0.00001
        wind_vol = 0.5
        water_density = 0.00005
    elif mode == 'focus':
        freqs = [130.81, 164.81, 196.00, 246.94, 329.63]
        bell_density = 0.00008
        wind_vol = 0.2
        water_density = 0.0003
    else:
        freqs = [130.81, 196.00, 261.63, 329.63, 392.00]
        bell_density = 0.00005
        wind_vol = 0.3
        water_density = 0.0002

    total_samples = int(duration_sec * sample_rate)

    # Create pad voices
    pads = []
    for i, f in enumerate(freqs):
        harmonics = [1.0, 2.0, 3.01, 4.02, 5.04]
        pad = ZenPad(f, harmonics, detune=0.003, seed=rng.randint(0, 99999))
        pads.append(pad)

    wind = WindSound(seed=rng.randint(0, 99999))
    water = WaterDrops(seed=rng.randint(0, 99999), density=water_density)
    bells = BellTone(seed=rng.randint(0, 99999), density=bell_density)

    # Master LFO for overall dynamics
    master_lfo = SmoothNoise(seed=rng.randint(0, 99999))
    master_lfo.speed = 0.00005

    for i in range(total_samples):
        master_vol = 0.6 + 0.4 * (0.5 + 0.5 * master_lfo.next())

        # Mix pads
        pad_sum = sum(p.next() for p in pads) / len(pads)

        # Add layers
        w = wind.next() * wind_vol
        wd = water.next()
        bl = bells.next()

        mix = (pad_sum * 0.6 + w * 0.3 + wd + bl * 0.5) * master_vol
        mix = clamp(mix * 0.7)

        yield mix


def write_wav(filename, duration_sec, mode='meditation'):
    """Write zen audio to WAV file."""
    sample_rate = SAMPLE_RATE
    total_samples = int(duration_sec * sample_rate)

    print(f"Generating {duration_sec}s of '{mode}' audio...")
    print(f"Output: {filename}")
    print(f"Sample rate: {sample_rate} Hz")

    with wave.open(filename, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.setnframes(total_samples)

        buf_size = 4096
        buf = []
        count = 0

        for sample in generate_zen_audio(duration_sec, mode, sample_rate):
            int_val = int(clamp(sample, -1.0, 1.0) * MAX_AMP)
            buf.append(struct.pack('<h', int_val))
            count += 1

            if len(buf) >= buf_size:
                wf.writeframes(b''.join(buf))
                buf = []
                if count % (sample_rate * 10) == 0:
                    pct = count * 100 // total_samples
                    elapsed = count // sample_rate
                    print(f"  [{pct:3d}%] {elapsed}s / {duration_sec}s", flush=True)

        if buf:
            wf.writeframes(b''.join(buf))

    size_mb = os.path.getsize(filename) / (1024 * 1024)
    print(f"Done! {filename} ({size_mb:.1f} MB)")


def main():
    parser = argparse.ArgumentParser(description='Zen Audio Generator')
    parser.add_argument('-d', '--duration', type=int, default=3600,
                        help='Duration in seconds (default: 3600 = 1 hour)')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='Output WAV file (default: zen_<mode>.wav)')
    parser.add_argument('-m', '--mode', type=str, default='meditation',
                        choices=['meditation', 'sleep', 'focus', 'nature'],
                        help='Audio style (default: meditation)')
    parser.add_argument('--batch', type=int, default=None,
                        help='Generate N sequential files (for long sessions)')
    parser.add_argument('--batch-dir', type=str, default='audio_output',
                        help='Directory for batch output')
    args = parser.parse_args()

    if args.batch:
        os.makedirs(args.batch_dir, exist_ok=True)
        for i in range(args.batch):
            fname = os.path.join(args.batch_dir, f'zen_{args.mode}_{i+1:03d}.wav')
            write_wav(fname, args.duration, args.mode)
        print(f"\nBatch complete: {args.batch} files in {args.batch_dir}/")
    else:
        output = args.output or f'zen_{args.mode}.wav'
        write_wav(output, args.duration, args.mode)


if __name__ == '__main__':
    main()
