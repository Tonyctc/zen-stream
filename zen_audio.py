#!/usr/bin/env python3
"""
Zen Audio Generator v2 — Procedural ambient/meditation audio.
Pure Python, zero dependencies.

New in v2:
  - Stereo output with spatial width
  - Schroeder reverb (allpass + comb filters)
  - Binaural beats (432Hz base + delta/theta/alpha)
  - Richer waveforms (saw-triangle hybrid, FM, vibrato)
  - ADSR envelopes for all voices
  - Chorus effect
  - Low-pass filter with resonance

Usage:
    python3 zen_audio.py                         # 1 hour meditation
    python3 zen_audio.py -d 7200 -m sleep        # 2 hours sleep
    python3 zen_audio.py --tuning 432             # 432Hz tuning
"""

import wave
import struct
import math
import random
import argparse
import sys
import os
import time as _time

SAMPLE_RATE = 44100
MAX_AMP = 32767
PI2 = 2.0 * math.pi


def clamp(val, lo=-1.0, hi=1.0):
    return max(lo, min(hi, val))


# ─── Core DSP Components ─────────────────────────────────────────────

class OnePoleLP:
    """Simple one-pole low-pass filter."""

    def __init__(self, cutoff=0.1):
        self.cutoff = cutoff
        self.state = 0.0

    def process(self, x):
        self.state += self.cutoff * (x - self.state)
        return self.state

    def set_cutoff(self, c):
        self.cutoff = clamp(c, 0.001, 1.0)


class BiquadLP:
    """Biquad low-pass filter with resonance."""

    def __init__(self, freq=1000, q=0.707, sample_rate=SAMPLE_RATE):
        self.sample_rate = sample_rate
        self.x1 = self.x2 = self.y1 = self.y2 = 0.0
        self.set_params(freq, q)

    def set_params(self, freq, q):
        w0 = PI2 * freq / self.sample_rate
        alpha = math.sin(w0) / (2.0 * q)
        cosw = math.cos(w0)
        a0 = 1.0 + alpha
        self.b0 = ((1.0 - cosw) / 2.0) / a0
        self.b1 = (1.0 - cosw) / a0
        self.b2 = self.b0
        self.a1 = (-2.0 * cosw) / a0
        self.a2 = (1.0 - alpha) / a0

    def process(self, x):
        y = self.b0 * x + self.b1 * self.x1 + self.b2 * self.x2 \
            - self.a1 * self.y1 - self.a2 * self.y2
        self.x2, self.x1 = self.x1, x
        self.y2, self.y1 = self.y1, y
        return y


class CombFilter:
    """Comb filter for Schroeder reverb."""

    def __init__(self, delay_samples, feedback=0.5):
        self.buffer = [0.0] * delay_samples
        self.buf_size = delay_samples
        self.pos = 0
        self.feedback = feedback
        self.filter_state = 0.0
        self.damp = 0.5

    def process(self, x):
        delayed = self.buffer[self.pos]
        # Damped feedback (lowpass in feedback loop)
        self.filter_state = delayed * (1.0 - self.damp) + self.filter_state * self.damp
        self.buffer[self.pos] = x + self.filter_state * self.feedback
        self.pos = (self.pos + 1) % self.buf_size
        return delayed


class AllPassFilter:
    """Allpass filter for Schroeder reverb diffusion."""

    def __init__(self, delay_samples, feedback=0.5):
        self.buffer = [0.0] * delay_samples
        self.buf_size = delay_samples
        self.pos = 0
        self.feedback = feedback

    def process(self, x):
        delayed = self.buffer[self.pos]
        out = -x + delayed
        self.buffer[self.pos] = x + delayed * self.feedback
        self.pos = (self.pos + 1) % self.buf_size
        return out


class SchroederReverb:
    """Schroeder reverb: 4 parallel combs + 2 series allpasses."""

    def __init__(self, sample_rate=SAMPLE_RATE, room_size=0.7, damping=0.5,
                 wet=0.35, dry=0.7, pre_delay_ms=30):
        self.sample_rate = sample_rate
        self.wet = wet
        self.dry = dry

        # Pre-delay buffer
        pre_delay = int(pre_delay_ms * sample_rate / 1000)
        self.pre_delay_buf = [0.0] * max(pre_delay, 1)
        self.pre_delay_pos = 0

        # Comb filter delays (tuned for room size)
        base = room_size
        comb_delays = [
            int(sample_rate * base * 0.025),
            int(sample_rate * base * 0.031),
            int(sample_rate * base * 0.037),
            int(sample_rate * base * 0.043),
        ]
        self.combs = []
        for d in comb_delays:
            c = CombFilter(max(d, 1), feedback=0.6 + room_size * 0.25)
            c.damp = damping
            self.combs.append(c)

        # Allpass delays
        self.allpasses = [
            AllPassFilter(max(int(sample_rate * 0.005), 1), feedback=0.5),
            AllPassFilter(max(int(sample_rate * 0.0017), 1), feedback=0.5),
        ]

    def process(self, x):
        # Pre-delay
        delayed = self.pre_delay_buf[self.pre_delay_pos]
        self.pre_delay_buf[self.pre_delay_pos] = x
        self.pre_delay_pos = (self.pre_delay_pos + 1) % len(self.pre_delay_buf)

        # Parallel combs
        comb_sum = sum(c.process(delayed) for c in self.combs) * 0.25

        # Series allpasses
        out = comb_sum
        for ap in self.allpasses:
            out = ap.process(out)

        return x * self.dry + out * self.wet


class StereoChorus:
    """Simple stereo chorus using modulated delay."""

    def __init__(self, sample_rate=SAMPLE_RATE, depth=0.003, rate=0.3):
        self.sample_rate = sample_rate
        self.max_delay = int(sample_rate * 0.03)  # 30ms max
        self.buffer_l = [0.0] * self.max_delay
        self.buffer_r = [0.0] * self.max_delay
        self.write_pos = 0
        self.phase_l = 0.0
        self.phase_r = math.pi * 0.5  # 90 degrees offset
        self.rate = rate
        self.depth = depth * sample_rate

    def process(self, mono):
        # Write to circular buffer
        self.buffer_l[self.write_pos] = mono
        self.buffer_r[self.write_pos] = mono

        # Modulated read positions
        delay_l = self.max_delay - int(self.depth * (1.0 + math.sin(self.phase_l)) * 0.5)
        delay_r = self.max_delay - int(self.depth * (1.0 + math.sin(self.phase_r)) * 0.5)

        read_l = (self.write_pos - delay_l) % self.max_delay
        read_r = (self.write_pos - delay_r) % self.max_delay

        out_l = self.buffer_l[read_l]
        out_r = self.buffer_r[read_r]

        self.write_pos = (self.write_pos + 1) % self.max_delay
        self.phase_l += PI2 * self.rate / self.sample_rate
        self.phase_r += PI2 * self.rate / self.sample_rate

        return out_l, out_r


# ─── Oscillators ──────────────────────────────────────────────────────

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


class RichOscillator:
    """Multi-waveform oscillator with vibrato and FM."""

    def __init__(self, freq, waveform='sine', detune_cents=0, sample_rate=SAMPLE_RATE):
        self.freq = freq * (2.0 ** (detune_cents / 1200.0))
        self.phase = 0.0
        self.sample_rate = sample_rate
        self.waveform = waveform
        self.vibrato_lfo = SmoothNoise(seed=random.randint(0, 99999))
        self.vibrato_lfo.speed = 0.001
        self.vibrato_depth = 0.002

    def next(self, fm_amount=0.0, fm_signal=0.0):
        vibrato = self.vibrato_lfo.next() * self.vibrato_depth
        actual_freq = self.freq * (1.0 + vibrato + fm_amount * fm_signal)
        self.phase += PI2 * actual_freq / self.sample_rate
        if self.phase > PI2:
            self.phase -= PI2

        t = self.phase / PI2  # normalized [0,1]

        if self.waveform == 'sine':
            return math.sin(self.phase)
        elif self.waveform == 'triangle':
            return 2.0 * abs(2.0 * t - 1.0) - 1.0
        elif self.waveform == 'sawtooth':
            return 2.0 * t - 1.0
        elif self.waveform == 'warm_saw':
            # Band-limited sawtooth approximation (3 harmonics)
            val = math.sin(self.phase)
            val += 0.5 * math.sin(2 * self.phase)
            val += 0.25 * math.sin(3 * self.phase)
            val += 0.125 * math.sin(4 * self.phase)
            return val / 1.875
        elif self.waveform == 'soft_square':
            # Soft square using tanh of sine
            return math.tanh(2.0 * math.sin(self.phase))
        else:
            return math.sin(self.phase)


class BinauralGenerator:
    """Binaural beat generator — slight freq difference L vs R."""

    def __init__(self, base_freq=432.0, beat_freq=4.0, sample_rate=SAMPLE_RATE):
        self.freq_l = base_freq - beat_freq * 0.5
        self.freq_r = base_freq + beat_freq * 0.5
        self.phase_l = 0.0
        self.phase_r = 0.0
        self.sample_rate = sample_rate
        self.amp_lfo = SmoothNoise(seed=777)
        self.amp_lfo.speed = 0.0002

    def next(self):
        amp = 0.04 + 0.03 * (0.5 + 0.5 * self.amp_lfo.next())
        self.phase_l += PI2 * self.freq_l / self.sample_rate
        self.phase_r += PI2 * self.freq_r / self.sample_rate
        if self.phase_l > PI2:
            self.phase_l -= PI2
        if self.phase_r > PI2:
            self.phase_r -= PI2
        return (math.sin(self.phase_l) * amp,
                math.sin(self.phase_r) * amp)


# ─── ADSR Envelope ────────────────────────────────────────────────────

class ADSREnvelope:
    """Smooth ADSR envelope with exponential curves."""

    def __init__(self, attack=0.1, decay=0.1, sustain=0.7, release=0.3,
                 sample_rate=SAMPLE_RATE):
        self.a = max(int(attack * sample_rate), 1)
        self.d = max(int(decay * sample_rate), 1)
        self.s = sustain
        self.r = max(int(release * sample_rate), 1)
        self.pos = 0

    def next(self):
        if self.pos < self.a:
            # Exponential attack
            t = self.pos / self.a
            val = t * t
        elif self.pos < self.a + self.d:
            # Exponential decay to sustain
            t = (self.pos - self.a) / self.d
            val = 1.0 - (1.0 - self.s) * t * t
        else:
            val = self.s
        self.pos += 1
        return val

    def get_release(self, release_samples):
        """Get release envelope values."""
        for i in range(release_samples):
            t = i / release_samples
            yield self.s * (1.0 - t) * (1.0 - t)


# ─── Voice Layers ─────────────────────────────────────────────────────

class ZenPadLayer:
    """Rich pad layer with multiple detuned oscillators + FM."""

    def __init__(self, base_freq, waveform='warm_saw', num_voices=3,
                 detune_cents=4, seed=None, sample_rate=SAMPLE_RATE):
        self.rng = random.Random(seed)
        self.oscillators = []
        spread = detune_cents
        for i in range(num_voices):
            cents = spread * (i - (num_voices - 1) * 0.5) / max(num_voices - 1, 1)
            osc = RichOscillator(base_freq, waveform=waveform,
                                 detune_cents=cents, sample_rate=sample_rate)
            self.oscillators.append(osc)

        # FM modulator for subtle shimmer
        self.fm_mod = RichOscillator(base_freq * 2.0, waveform='sine',
                                      sample_rate=sample_rate)
        self.fm_depth = 0.001

        # Slow amp modulation
        self.amp_lfo = SmoothNoise(seed=seed)
        self.amp_lfo.speed = 0.0002

        # Low-pass for warmth
        self.lpf = OnePoleLP(cutoff=0.15)

    def next(self):
        amp = 0.5 + 0.5 * self.amp_lfo.next()
        fm = self.fm_mod.next() * self.fm_depth

        val = 0.0
        for osc in self.oscillators:
            val += osc.next(fm_amount=0.0005, fm_signal=fm)
        val /= len(self.oscillators)

        # Warm low-pass
        val = self.lpf.process(val)

        return val * amp * 0.25


class WindLayer:
    """Layered wind with bandpass filtering and slow dynamics."""

    def __init__(self, seed=None, sample_rate=SAMPLE_RATE):
        self.rng = random.Random(seed)
        self.noise_buf = [self.rng.gauss(0, 1) for _ in range(4096)]
        self.noise_pos = 0

        # Multiple bandpass stages
        self.bp1 = BiquadLP(freq=400, q=2.0, sample_rate=sample_rate)
        self.bp2 = BiquadLP(freq=800, q=1.5, sample_rate=sample_rate)
        self.bp3 = BiquadLP(freq=200, q=3.0, sample_rate=sample_rate)

        self.vol_lfo = SmoothNoise(seed=seed)
        self.vol_lfo.speed = 0.00015
        self.freq_lfo = SmoothNoise(seed=seed)
        self.freq_lfo.speed = 0.00008

    def next(self):
        # Read from noise buffer with slow position drift
        n = self.noise_buf[self.noise_pos % len(self.noise_buf)]
        self.noise_pos += 1

        # Modulate filter frequency
        freq_mod = 0.5 + 0.5 * self.freq_lfo.next()
        self.bp1.set_params(200 + 600 * freq_mod, 2.0)
        self.bp2.set_params(400 + 800 * (1 - freq_mod), 1.5)

        # Multi-stage filtering
        x = n * 0.015
        x = self.bp1.process(x)
        x += self.bp2.process(n * 0.01) * 0.5
        x += self.bp3.process(n * 0.008) * 0.3

        # Volume modulation
        vol = 0.15 + 0.35 * (0.5 + 0.5 * self.vol_lfo.next())

        return clamp(x * vol * 12.0)


class RainLayer:
    """Rain-like texture using filtered noise bursts."""

    def __init__(self, seed=None, density=0.01, sample_rate=SAMPLE_RATE):
        self.rng = random.Random(seed)
        self.density = density
        self.bp = BiquadLP(freq=3000, q=0.5, sample_rate=sample_rate)
        self.hp = BiquadLP(freq=8000, q=0.3, sample_rate=sample_rate)
        self.amp_lfo = SmoothNoise(seed=seed)
        self.amp_lfo.speed = 0.0003

    def next(self):
        if self.rng.random() < self.density:
            n = self.rng.gauss(0, 1) * 0.03
        else:
            n = 0.0
        x = self.bp.process(n)
        amp = 0.5 + 0.5 * self.amp_lfo.next()
        return clamp(x * amp * 5.0)


class WaterDropsLayer:
    """Water drops with natural pitch glide."""

    def __init__(self, seed=None, density=0.0003, sample_rate=SAMPLE_RATE):
        self.rng = random.Random(seed)
        self.density = density
        self.drops = []

    def next(self):
        if self.rng.random() < self.density:
            base_freq = self.rng.uniform(600, 2000)
            self.drops.append({
                'freq': base_freq,
                'freq_glide': base_freq * self.rng.uniform(0.3, 0.7),
                'phase': 0.0,
                'amp': self.rng.uniform(0.04, 0.12),
                'decay': self.rng.uniform(0.003, 0.01),
                'age': 0,
                'duration': self.rng.randint(800, 3000),
            })

        val = 0.0
        alive = []
        for d in self.drops:
            t = d['age'] / d['duration'] if d['duration'] > 0 else 1
            # Pitch glide
            freq = d['freq'] + (d['freq_glide'] - d['freq']) * min(t * 2, 1.0)
            d['phase'] += PI2 * freq / SAMPLE_RATE
            env = math.exp(-d['age'] * d['decay'])
            # Slight FM for organic feel
            val += math.sin(d['phase'] + 0.3 * math.sin(d['phase'] * 0.5)) * d['amp'] * env
            d['age'] += 1
            if env > 0.001 and d['age'] < d['duration']:
                alive.append(d)
        self.drops = alive
        return clamp(val)


class SingingBowlLayer:
    """Singing bowl / bell tones with inharmonic partials."""

    def __init__(self, seed=None, density=0.00005, sample_rate=SAMPLE_RATE):
        self.rng = random.Random(seed)
        self.density = density
        self.bowls = []

    def next(self):
        if self.rng.random() < self.density:
            # Singing bowl partials (inharmonic ratios)
            base = self.rng.choice([174.61, 220.00, 261.63, 329.63, 392.00, 523.25])
            partials = [
                (base * 1.0, 1.0),
                (base * 2.0, 0.5),
                (base * 3.01, 0.3),
                (base * 4.07, 0.15),
                (base * 5.19, 0.08),
                (base * 6.37, 0.04),
            ]
            self.bowls.append({
                'partials': partials,
                'decay': self.rng.uniform(0.0001, 0.0005),
                'age': 0,
                'amp': self.rng.uniform(0.06, 0.18),
                'stereo_pan': self.rng.uniform(-1, 1),
            })

        val_l = 0.0
        val_r = 0.0
        alive = []
        for b in self.bowls:
            env = math.exp(-b['age'] * b['decay'])
            sample = 0.0
            for freq, amp in b['partials']:
                phase = PI2 * freq * b['age'] / SAMPLE_RATE
                sample += math.sin(phase) * amp
            total = sample * b['amp'] * env

            # Simple pan
            pan = b['stereo_pan']
            val_l += total * (1.0 - max(0, pan)) * 0.7
            val_r += total * (1.0 + min(0, pan)) * 0.7

            b['age'] += 1
            if env > 0.001:
                alive.append(b)
        self.bowls = alive
        return clamp(val_l * 0.5), clamp(val_r * 0.5)


# ─── Mode Configurations ─────────────────────────────────────────────

MODES = {
    'meditation': {
        'freqs': [130.81, 174.61, 196.00, 261.63, 329.63],
        'waveform': 'warm_saw',
        'binaural_freq': 6.0,    # Theta (deep meditation)
        'wind_vol': 0.25,
        'water_density': 0.0002,
        'rain_density': 0.005,
        'bowl_density': 0.00004,
        'reverb_size': 0.8,
        'reverb_damping': 0.4,
        'chorus_depth': 0.004,
        'title': 'Meditation',
    },
    'sleep': {
        'freqs': [55.00, 82.41, 110.00, 146.83],
        'waveform': 'triangle',
        'binaural_freq': 2.0,    # Delta (deep sleep)
        'wind_vol': 0.45,
        'water_density': 0.00005,
        'rain_density': 0.003,
        'bowl_density': 0.00001,
        'reverb_size': 0.9,
        'reverb_damping': 0.6,
        'chorus_depth': 0.002,
        'title': 'Deep Sleep',
    },
    'focus': {
        'freqs': [164.81, 196.00, 246.94, 329.63],
        'waveform': 'warm_saw',
        'binaural_freq': 10.0,   # Alpha (alert relaxation)
        'wind_vol': 0.15,
        'water_density': 0.0003,
        'rain_density': 0.008,
        'bowl_density': 0.00006,
        'reverb_size': 0.6,
        'reverb_damping': 0.3,
        'chorus_depth': 0.003,
        'title': 'Deep Focus',
    },
    'nature': {
        'freqs': [130.81, 196.00, 261.63, 392.00],
        'waveform': 'triangle',
        'binaural_freq': 7.83,   # Schumann resonance
        'wind_vol': 0.35,
        'water_density': 0.0004,
        'rain_density': 0.01,
        'bowl_density': 0.00003,
        'reverb_size': 0.75,
        'reverb_damping': 0.5,
        'chorus_depth': 0.005,
        'title': 'Nature Sounds',
    },
}


# ─── Main Generator ──────────────────────────────────────────────────

def generate_stereo_audio(duration_sec, mode='meditation', tuning=432,
                          sample_rate=SAMPLE_RATE):
    """
    Generate stereo procedural zen audio.
    Yields (left, right) sample pairs as floats in [-1, 1].
    """
    rng = random.Random(42)
    cfg = MODES.get(mode, MODES['meditation'])
    total_samples = int(duration_sec * sample_rate)

    # Frequency adjustment for 432Hz tuning
    tuning_ratio = tuning / 440.0

    # ─── Build layers ────────────────────────────────────────
    pads = []
    for f in cfg['freqs']:
        adj_f = f * tuning_ratio
        layer = ZenPadLayer(adj_f, waveform=cfg['waveform'],
                            num_voices=3, detune_cents=5,
                            seed=rng.randint(0, 99999),
                            sample_rate=sample_rate)
        pads.append(layer)

    wind = WindLayer(seed=rng.randint(0, 99999), sample_rate=sample_rate)
    rain = RainLayer(seed=rng.randint(0, 99999), density=cfg['rain_density'],
                     sample_rate=sample_rate)
    drops = WaterDropsLayer(seed=rng.randint(0, 99999),
                            density=cfg['water_density'],
                            sample_rate=sample_rate)
    bowls = SingingBowlLayer(seed=rng.randint(0, 99999),
                              density=cfg['bowl_density'],
                              sample_rate=sample_rate)

    binaural = BinauralGenerator(base_freq=tuning,
                                  beat_freq=cfg['binaural_freq'],
                                  sample_rate=sample_rate)

    chorus = StereoChorus(sample_rate=sample_rate,
                          depth=cfg['chorus_depth'], rate=0.25)

    reverb_l = SchroederReverb(sample_rate=sample_rate,
                                room_size=cfg['reverb_size'],
                                damping=cfg['reverb_damping'],
                                wet=0.35, dry=0.65)
    reverb_r = SchroederReverb(sample_rate=sample_rate,
                                room_size=cfg['reverb_size'] * 1.02,
                                damping=cfg['reverb_damping'],
                                wet=0.35, dry=0.65)

    master_lfo = SmoothNoise(seed=rng.randint(0, 99999))
    master_lfo.speed = 0.00003

    for i in range(total_samples):
        master_vol = 0.65 + 0.35 * (0.5 + 0.5 * master_lfo.next())

        # ─── Mix mono elements ───────────────────────────────
        pad_sum = sum(p.next() for p in pads) / len(pads)
        w = wind.next() * cfg['wind_vol']
        r = rain.next()
        d = drops.next()
        bowl_l, bowl_r = bowls.next()

        mono_mix = pad_sum * 0.55 + w * 0.25 + r * 0.15 + d

        # ─── Stereo chorus ───────────────────────────────────
        ch_l, ch_r = chorus.process(mono_mix)

        # ─── Binaural beats (L/R differ) ─────────────────────
        bin_l, bin_r = binaural.next()

        # ─── Combine L/R ─────────────────────────────────────
        left = ch_l + bin_l + bowl_l * 0.5
        right = ch_r + bin_r + bowl_r * 0.5

        # ─── Reverb (separate L/R) ───────────────────────────
        left = reverb_l.process(left)
        right = reverb_r.process(right)

        # ─── Master volume ───────────────────────────────────
        left = clamp(left * master_vol * 0.75)
        right = clamp(right * master_vol * 0.75)

        yield left, right


# ─── WAV Writer ──────────────────────────────────────────────────────

def write_wav(filename, duration_sec, mode='meditation', tuning=432):
    """Write stereo zen audio to WAV file."""
    sample_rate = SAMPLE_RATE
    total_samples = int(duration_sec * sample_rate)

    print(f"Generating {duration_sec}s of '{mode}' audio (stereo)...")
    print(f"Output: {filename}")
    print(f"Sample rate: {sample_rate} Hz | Tuning: {tuning}Hz")
    print(f"Binaural: {MODES[mode]['binaural_freq']}Hz ({mode})")

    t_start = _time.time()

    with wave.open(filename, 'w') as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.setnframes(total_samples)

        buf_size = 4096
        buf = []
        count = 0

        for left, right in generate_stereo_audio(duration_sec, mode, tuning, sample_rate):
            l = int(clamp(left, -1.0, 1.0) * MAX_AMP)
            r = int(clamp(right, -1.0, 1.0) * MAX_AMP)
            buf.append(struct.pack('<hh', l, r))
            count += 1

            if len(buf) >= buf_size:
                wf.writeframes(b''.join(buf))
                buf = []
                if count % (sample_rate * 10) == 0:
                    pct = count * 100 // total_samples
                    elapsed = count // sample_rate
                    speed = count / (_time.time() - t_start) if _time.time() > t_start else 0
                    eta = (total_samples - count) / speed if speed > 0 else 0
                    print(f"  [{pct:3d}%] {elapsed}s / {duration_sec}s | "
                          f"{speed:.0f} samples/s | ETA: {eta:.0f}s",
                          flush=True)

        if buf:
            wf.writeframes(b''.join(buf))

    size_mb = os.path.getsize(filename) / (1024 * 1024)
    elapsed = _time.time() - t_start
    print(f"Done! {filename} ({size_mb:.1f} MB) in {elapsed:.1f}s")


# ─── CLI ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Zen Audio Generator v2')
    parser.add_argument('-d', '--duration', type=int, default=3600,
                        help='Duration in seconds (default: 3600)')
    parser.add_argument('-o', '--output', type=str, default=None,
                        help='Output WAV file')
    parser.add_argument('-m', '--mode', type=str, default='meditation',
                        choices=list(MODES.keys()),
                        help='Audio mode (default: meditation)')
    parser.add_argument('--tuning', type=float, default=432,
                        help='Base tuning frequency in Hz (default: 432)')
    parser.add_argument('--batch', type=int, default=None,
                        help='Generate N sequential files')
    parser.add_argument('--batch-dir', type=str, default='audio_output',
                        help='Directory for batch output')
    args = parser.parse_args()

    if args.batch:
        os.makedirs(args.batch_dir, exist_ok=True)
        for i in range(args.batch):
            fname = os.path.join(args.batch_dir, f'zen_{args.mode}_{i+1:03d}.wav')
            write_wav(fname, args.duration, args.mode, args.tuning)
        print(f"\nBatch complete: {args.batch} files in {args.batch_dir}/")
    else:
        output = args.output or f'zen_{args.mode}.wav'
        write_wav(output, args.duration, args.mode, args.tuning)


if __name__ == '__main__':
    main()
