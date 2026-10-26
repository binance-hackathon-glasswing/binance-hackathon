"""Synthesize the voiceover and word timings for the LARP layers video.

Needs piper-tts (with onnx, for alignments) and a Piper voice; neither is a project
dependency. See README.md.

Usage: python narrate.py VOICE.onnx out_dir
Writes out_dir/voice.wav (22.05 kHz mono) and out_dir/captions.json.
"""
import json
import re
import sys
import wave

import numpy as np
from piper import PiperVoice, SynthesisConfig

# (slot start, slot end, spoken line, words to highlight). Slots match the scene
# cuts in render.html: hook 0-4 s, layers every 3 s from 4 s, outro 25-30 s.
SCRIPT = [
    (0.15, 2.0, "POV: your AI trades real money.", {"AI", "real", "money"}),
    (2.0, 3.95, "So you gave it seven layers of trust issues.", {"seven", "layers", "trust", "issues"}),
    (4.15, 6.95, "One, sources. Every filing, timestamped and hashed.", {"sources", "timestamped", "hashed"}),
    (7.15, 9.95, "Two, the LLM. It reads everything. Trades nothing.", {"LLM", "reads", "nothing"}),
    (10.15, 12.95, "Three, the verifier. No evidence? The claim gets cut.", {"verifier", "cut"}),
    (13.15, 15.95, "Four, strategy. Equal weight. Boring on purpose.", {"strategy", "Equal", "weight", "Boring"}),
    (16.15, 18.95, "Five, risk governor. Pure code. No vibes.", {"risk", "governor", "code", "vibes"}),
    (19.15, 21.95, "Six, execution. Write it down before you sign it.", {"execution", "Write", "sign"}),
    (22.15, 24.95, "Seven, audit. Every round logged. Even the holds.", {"audit", "logged", "holds"}),
    (25.15, 27.3, "Any layer can stop a trade.", {"stop"}),
    (27.35, 29.7, "None of them can force one.", {"force"}),
]

PUNCT = set(",.?!:;")


def synth(voice, text, scale):
    audio, words = [], []
    t = 0.0
    for chunk in voice.synthesize(text, SynthesisConfig(length_scale=scale), include_alignments=True):
        sr = chunk.sample_rate
        audio.append(chunk.audio_float_array)
        # group phonemes into words at spaces; punctuation-only groups are not words
        cur, start = [], t
        for a in chunk.phoneme_alignments or []:
            dur = a.num_samples / sr
            if a.phoneme == " ":
                if cur:
                    words.append((start, t))
                cur, start = [], t + dur
            elif a.phoneme in ("^", "$"):
                if a.phoneme == "^":
                    start = t + dur
            elif a.phoneme not in PUNCT:
                cur.append(a.phoneme)
            t += dur
        if cur:
            words.append((start, t))
        t = sum(len(x) for x in audio) / sr
    return np.concatenate(audio), sr, words


def trim(audio, sr, thresh=0.01):
    idx = np.flatnonzero(np.abs(audio) > thresh)
    lead = max(0, idx[0] - int(0.02 * sr))
    return audio[lead: idx[-1] + int(0.06 * sr)], lead / sr


def main():
    voice_path, out_dir = sys.argv[1], sys.argv[2]
    voice = PiperVoice.load(voice_path, include_alignments=True)
    total = None
    track, lines = None, []
    for start, end, text, highlight in SCRIPT:
        tokens = text.split()
        scale = 0.92
        while True:
            audio, sr, wtimes = synth(voice, text, scale)
            audio, lead = trim(audio, sr)
            if len(audio) / sr <= end - start or scale <= 0.78:
                break
            scale -= 0.03
        if track is None:
            total = int(30.0 * sr)
            track = np.zeros(total, dtype=np.float32)
        i = int(start * sr)
        track[i:i + len(audio)] += audio[: total - i]
        dur = len(audio) / sr
        if len(wtimes) != len(tokens):
            # alignment split differs from the text: fall back to timing by letters
            print(f"  alignment fallback ({len(wtimes)} vs {len(tokens)}): {text}")
            weights = np.array([len(re.sub(r"\W", "", w)) + 1 for w in tokens], float)
            edges = np.concatenate([[0], np.cumsum(weights)]) / weights.sum() * dur
            wtimes = [(edges[k] + lead, edges[k + 1] + lead) for k in range(len(tokens))]
        words = []
        for tok, (w0, w1) in zip(tokens, wtimes):
            bare = re.sub(r"[^\w']", "", tok)
            words.append({"w": tok, "t0": round(start + w0 - lead, 3), "t1": round(start + w1 - lead, 3),
                          "hl": bare in highlight})
        lines.append({"start": start, "end": round(max(end, start + dur), 3), "text": text, "words": words})
        print(f"{start:5.2f}-{start + dur:5.2f} (slot {end:5.2f}) x{scale:.2f}  {text}")
    peak = np.max(np.abs(track))
    track = track / peak * 0.9
    with wave.open(f"{out_dir}/voice.wav", "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((track * 32767).astype(np.int16).tobytes())
    with open(f"{out_dir}/captions.json", "w") as f:
        json.dump(lines, f, indent=1)


if __name__ == "__main__":
    main()
