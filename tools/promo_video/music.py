"""Synthesize the 30 s, 120 BPM soundtrack for the LARP layers video.

Original audio built from numpy oscillators and noise (no samples, no licensing).
Timeline matches render.html: hook 0-4 s, drop at 4.0 s, layer cuts every 3 s
(7, 10, ... 22 s), outro impact at 25.0 s.

Usage: python music.py out.wav
"""
import sys
import wave

import numpy as np

SR = 44100
BPM = 120
BEAT = 60 / BPM
DUR = 30.0
N = int(SR * DUR)
rng = np.random.default_rng(7)

CUTS = [4.0, 7.0, 10.0, 13.0, 16.0, 19.0, 22.0, 25.0]
DROP, OUTRO = 4.0, 25.0


def t_arr(n):
    return np.arange(n) / SR


def add(buf, start, sig, gain=1.0):
    i = int(round(start * SR))
    if i >= len(buf):
        return
    j = min(len(buf), i + len(sig))
    buf[i:j] += sig[: j - i] * gain


def fft_filter(sig, lo=None, hi=None):
    spec = np.fft.rfft(sig)
    f = np.fft.rfftfreq(len(sig), 1 / SR)
    mask = np.ones_like(f)
    if lo:
        mask *= 1 / (1 + (lo / np.maximum(f, 1)) ** 4)
    if hi:
        mask *= 1 / (1 + (f / hi) ** 4)
    return np.fft.irfft(spec * mask, len(sig))


def kick(punch=1.0):
    t = t_arr(int(0.45 * SR))
    f = 45 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * 7)
    click = rng.standard_normal(len(t)) * np.exp(-t * 400) * 0.3
    return np.tanh((body + click) * 1.6 * punch)


def clap():
    t = t_arr(int(0.3 * SR))
    env = np.zeros_like(t)
    for k, d in enumerate([0, 0.011, 0.022]):
        env += (t >= d) * np.exp(-np.maximum(t - d, 0) * (180 if k < 2 else 22))
    return fft_filter(rng.standard_normal(len(t)), 900, 5000) * env * 0.9


def hat(open_=False):
    t = t_arr(int((0.22 if open_ else 0.05) * SR))
    n = fft_filter(rng.standard_normal(len(t)), 7000, None)
    return n * np.exp(-t * (16 if open_ else 90))


def pluck(freq, dur=0.22):
    t = t_arr(int(dur * SR))
    out = np.zeros_like(t)
    for k in range(1, 14):
        if k * freq > 12000:
            break
        out += np.sin(2 * np.pi * k * freq * t) / k * np.exp(-t * (9 + 5.5 * k))
    return out * 0.5


def saw_pad(freqs, dur):
    t = t_arr(int(dur * SR))
    out = np.zeros_like(t)
    for f in freqs:
        for det in (-0.12, 0.0, 0.12):
            ff = f * 2 ** (det / 12)
            out += 2 * ((t * ff) % 1.0) - 1
    env = np.minimum(1, t / 0.05) * np.minimum(1, (dur - t) / 0.1)
    return out * env / (3 * len(freqs))


def sub(freq, dur):
    t = t_arr(int(dur * SR))
    s = np.sin(2 * np.pi * freq * t) + 0.25 * np.tanh(3 * np.sin(2 * np.pi * freq * t))
    env = np.minimum(1, t / 0.01) * np.minimum(1, (dur - t) / 0.02)
    return s * env


def noise_riser(dur):
    t = t_arr(int(dur * SR))
    n = rng.standard_normal(len(t))
    # three bands that fade in successively: a cheap swept filter
    out = np.zeros_like(t)
    p = t / dur
    for lo, hi, w in [(300, 1200, 1 - p), (1200, 4000, np.sin(np.pi * p)), (4000, 12000, p)]:
        out += fft_filter(n, lo, hi) * w
    tone = np.sin(2 * np.pi * np.cumsum(200 + 1800 * p ** 2) / SR) * 0.25
    return (out * 0.6 + tone) * p ** 2


def whoosh(dur=0.5):
    t = t_arr(int(dur * SR))
    n = fft_filter(rng.standard_normal(len(t)), 1500, 9000)
    env = np.sin(np.pi * t / dur) ** 2
    return n * env


def impact():
    t = t_arr(int(1.6 * SR))
    boom = np.sin(2 * np.pi * np.cumsum(30 + 60 * np.exp(-t * 6)) / SR) * np.exp(-t * 2.2)
    crash = fft_filter(rng.standard_normal(len(t)), 3000, None) * np.exp(-t * 2.8) * 0.5
    return np.tanh(boom * 1.4) + crash


def glitch_blip():
    t = t_arr(int(0.12 * SR))
    sq = np.sign(np.sin(2 * np.pi * 1760 * t)) * (np.floor(t * 80) % 2)
    return sq * np.exp(-t * 18) * 0.35


# chords per 2 s bar: Am  F  C  G  (i VI III VII)
CHORDS = [
    (55.00, [220.0, 261.63, 329.63]),
    (43.65, [174.61, 220.0, 261.63]),
    (65.41, [261.63, 329.63, 392.0]),
    (49.00, [196.0, 246.94, 293.66]),
]

drums = np.zeros(N)
bass = np.zeros(N)
music = np.zeros(N)
fx = np.zeros(N)

n_beats = int(DUR / BEAT)
for b in range(n_beats):
    tb = b * BEAT
    full = tb >= DROP
    if full and not (OUTRO - 1.0 <= tb < OUTRO) and tb < DUR - 0.5:
        add(drums, tb, kick(1.15 if tb in CUTS else 1.0), 0.95)
        if b % 2 == 1:
            add(drums, tb, clap(), 0.45)
        add(drums, tb + BEAT / 2, hat(True), 0.16)
    for s in range(4):
        ts = tb + s * BEAT / 4
        if tb >= 1.0 and tb < DUR - 0.5:
            add(drums, ts, hat(), (0.13 if s % 2 else 0.2) * (1.0 if full else 0.6))

# hook: soft kick on the downbeats from 2 s, snare roll into the drop
for tb in (2.0, 2.5, 3.0):
    add(drums, tb, kick(0.7), 0.6)
roll_t = 3.0
step = BEAT / 2
while roll_t < DROP - 0.13:
    add(drums, roll_t, clap(), 0.18 + 0.35 * (roll_t - 3.0))
    roll_t += step
    step = max(BEAT / 8, step * 0.72)
# same roll before the outro impact
roll_t, step = OUTRO - 1.0, BEAT / 2
while roll_t < OUTRO - 0.1:
    add(drums, roll_t, clap(), 0.2 + 0.4 * (roll_t - (OUTRO - 1.0)))
    roll_t += step
    step = max(BEAT / 8, step * 0.72)

# sidechain envelope: duck everything tonal on each kick after the drop
duck = np.ones(N)
for b in range(n_beats):
    tb = b * BEAT
    if tb >= DROP:
        i = int(tb * SR)
        d = t_arr(int(BEAT * SR))
        seg = 1 - 0.75 * np.exp(-d * 9)
        j = min(N, i + len(seg))
        duck[i:j] = np.minimum(duck[i:j], seg[: j - i])

n_bars = int(DUR / (4 * BEAT))
for bar in range(n_bars):
    t0 = bar * 4 * BEAT
    root, chord = CHORDS[bar % 4]
    if t0 >= DROP:
        # offbeat-pumping sub bass in eighths
        for e in range(8):
            add(bass, t0 + e * BEAT / 2, sub(root * (2 if e % 4 == 3 else 1), BEAT / 2 * 0.9), 0.55)
    pad_gain = 0.10 if t0 >= DROP else 0.07
    add(music, t0, saw_pad(chord, 4 * BEAT), pad_gain)
    # 16th-note arp, rising/falling over the chord tones
    pattern = [0, 1, 2, 1, 2, 0, 1, 2, 0, 2, 1, 2, 0, 1, 2, 1]
    for s in range(16):
        ts = t0 + s * BEAT / 4
        f = chord[pattern[s]] * (2 if s % 8 >= 4 else 1)
        g = 0.16 if t0 >= DROP else 0.12
        if t0 < 1.0:
            g *= (ts / 1.0)
        add(music, ts, pluck(f), g)

music = fft_filter(music, 120, None)
# hook is lowpassed ("muffled") until 2 s, opening up into the drop
hook_n = int(DROP * SR)
muffled = fft_filter(music[:hook_n], None, 900)
mix_w = np.clip((t_arr(hook_n) - 1.6) / 2.4, 0, 1)
music[:hook_n] = muffled * (1 - mix_w) + music[:hook_n] * mix_w

# transitions
add(fx, 2.0, noise_riser(2.0), 0.35)
add(fx, OUTRO - 1.5, noise_riser(1.5), 0.32)
add(fx, DROP, impact(), 0.75)
add(fx, OUTRO, impact(), 0.8)
for c in CUTS[1:-1]:
    add(fx, c - 0.25, whoosh(0.5), 0.22)
    add(fx, c, glitch_blip(), 0.5)
add(fx, 2.0, glitch_blip(), 0.6)
add(fx, 0.0, glitch_blip(), 0.4)

tonal = (bass + music) * duck
# a beat of near-silence right before the drop and the outro hit
gap = np.ones(N)
for g in (DROP, OUTRO):
    i, j = int((g - 0.12) * SR), int(g * SR)
    gap[i:j] = 0.05
mix = (drums + tonal) * gap + fx

# ending: last half second fades out
tail = int(0.6 * SR)
mix[-tail:] *= np.linspace(1, 0, tail) ** 2

# stereo: hats/arp slightly wider via a short delay on the right channel
delay = int(0.011 * SR)
left = mix
right = mix.copy()
right[delay:] = (drums + tonal)[: -delay] * gap[: -delay] + fx[delay:]
right[-tail:] *= np.linspace(1, 0, tail) ** 2
stereo = np.stack([left, right], axis=1)
stereo = np.tanh(stereo * 1.2)
stereo /= np.max(np.abs(stereo)) * 1.05

out = sys.argv[1] if len(sys.argv) > 1 else "music.wav"
with wave.open(out, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((stereo * 32767).astype(np.int16).tobytes())
print("wrote", out)
