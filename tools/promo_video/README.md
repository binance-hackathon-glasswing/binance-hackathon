# LARP layers video (30 s, 9:16)

A short vertical video (TikTok/Reels/Shorts) showing LARP's seven layers and how they fit together.
Output: 1080×1920, 30 fps, H.264 + AAC, -14 LUFS. The rendered MP4 is not committed; re-render it with the steps below.

## Script (voiceover)

| Time | Scene | Line |
|---|---|---|
| 0–2 s | Hook: live wallet, candles | POV: your AI trades real money. |
| 2–4 s | Seven slabs stack up | So you gave it seven layers of trust issues. |
| 4–7 s | L01 Sources | One, sources. Every filing, timestamped and hashed. |
| 7–10 s | L02 Evidence LLM | Two, the LLM. It reads everything. Trades nothing. |
| 10–13 s | L03 Verifier | Three, the verifier. No evidence? The claim gets cut. |
| 13–16 s | L04 Strategy | Four, strategy. Equal weight. Boring on purpose. |
| 16–19 s | L05 Risk governor | Five, risk governor. Pure code. No vibes. |
| 19–22 s | L06 Execution | Six, execution. Write it down before you sign it. |
| 22–25 s | L07 Audit trail | Seven, audit. Every round logged. Even the holds. |
| 25–30 s | Tower lights up, LARP wordmark | Any layer can stop a trade. None of them can force one. |

On-screen facts come from the repo: the three evidence tools and the ≤ 6 calls / 60 s budget (`larp/intelligence/tools.py`, `config.py`, G-50); assessment-only LLM (IDEA-010/015); claim verification can only veto (G-53, P-09); equal weight 4 × 20%, top-up below 75%, hard trim at 25% (IDEA-037); drawdown ladder 8% / 12% → 40% and daily −3% (plan.md declared values); execution order version gate → write-ahead → signer → approve/confirm → re-quote → swap (plan.md §8); one ai-seeds round log per round, holds included, hourly anchor (F-99..F-101, IDEA-036).
The example claims, hashes, tx hashes, round numbers and the drawdown path are illustrative; the chart says "illustrative path".

## Build

Files: `music.py` (synthesized 120 BPM soundtrack, numpy only), `narrate.py` (voiceover and word timings with Piper TTS),
`render.html` (canvas renderer, `render(t)` per frame), `render.mjs` (Playwright → ffmpeg).

```bash
OUT=/some/scratch/dir
python music.py $OUT/music.wav

# Piper is not a project dependency: use a throwaway venv
python -m venv $OUT/ttsenv && $OUT/ttsenv/bin/pip install piper-tts onnx
curl -L -o $OUT/ryan.onnx      https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/en_US-ryan-high.onnx
curl -L -o $OUT/ryan.onnx.json https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high/en_US-ryan-high.onnx.json
$OUT/ttsenv/bin/python narrate.py $OUT/ryan.onnx $OUT      # writes voice.wav + captions.json

node render.mjs $OUT/captions.json $OUT/video_noaudio.mp4  # ~5 min; needs Playwright's Chromium, Inter Display, JetBrains Mono
node render.mjs $OUT/captions.json --stills $OUT 3.7 9.6   # optional: PNG stills to check a layout

ffmpeg -i $OUT/video_noaudio.mp4 -i $OUT/music.wav -i $OUT/voice.wav -filter_complex "\
[2:a]aresample=44100,aformat=channel_layouts=stereo,highpass=f=90,equalizer=f=3000:t=q:w=1:g=3,acompressor=threshold=-20dB:ratio=4:attack=5:release=60:makeup=4,asplit=2[v][vsc];\
[1:a]volume=0.45[m];[m][vsc]sidechaincompress=threshold=0.03:ratio=8:attack=15:release=300[md];\
[md][v]amix=inputs=2:normalize=0:duration=first,loudnorm=I=-14:TP=-1.5:LRA=11,aresample=44100[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k -movflags +faststart -shortest $OUT/larp_layers_tiktok.mp4
```

To change a line: edit `SCRIPT` in `narrate.py` (each line has a time slot; the script speeds a line up to at most
1/0.78× before letting it overrun), re-run it, then re-render, because captions are drawn from `captions.json`.
Scene cut times are shared by all three files (hook 0–4 s, a layer every 3 s from 4 s, outro at 25 s).
Key content stays inside TikTok's safe area (top ~200 px and bottom ~400 px and right ~120 px are covered by the app UI).
