// Render render.html to video frames with headless Chromium and pipe them to ffmpeg.
// Usage:
//   node render.mjs captions.json out.mp4            full 30 s video, no audio
//   node render.mjs captions.json --stills DIR t1 t2 ...   PNG stills at the given times
import { spawn } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const require = createRequire(import.meta.url);
const { chromium } = require('playwright');
const here = dirname(fileURLToPath(import.meta.url));
const FPS = 30, DURATION = 30;

const [captionsPath, ...rest] = process.argv.slice(2);
const captions = JSON.parse(readFileSync(captionsPath, 'utf8'));

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
await page.goto(pathToFileURL(join(here, 'render.html')).href);
await page.evaluate(async (c) => { await window.ready; window.setCaptions(c); }, captions);

const frame = (t) => page.evaluate((t) => { window.render(t); return document.getElementById('c').toDataURL('image/png'); }, t)
  .then((url) => Buffer.from(url.slice(url.indexOf(',') + 1), 'base64'));

if (rest[0] === '--stills') {
  const [, dir, ...times] = rest;
  for (const t of times) writeFileSync(join(dir, `still_${t}.png`), await frame(Number(t)));
} else {
  const out = rest[0];
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
    '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-r', String(FPS), out], { stdio: ['pipe', 'inherit', 'inherit'] });
  const started = Date.now();
  for (let f = 0; f < FPS * DURATION; f++) {
    const png = await frame(f / FPS);
    if (!ff.stdin.write(png)) await new Promise((r) => ff.stdin.once('drain', r));
    if (f % 90 === 0) console.log(`frame ${f}/${FPS * DURATION}  ${((Date.now() - started) / 1000).toFixed(0)}s`);
  }
  ff.stdin.end();
  await new Promise((r) => ff.on('close', r));
}
await browser.close();
