// Рендер ad.html → кадры → MP4 (ffmpeg). Запуск: node video/render.mjs
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
let chromium;
try { ({ chromium } = require('playwright')); } catch { ({ chromium } = require(require('node:child_process').execSync('npm root -g').toString().trim() + '/playwright')); }
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const dir = path.dirname(fileURLToPath(import.meta.url));
const FPS = 30;
const out = path.join(dir, 'out', 'silent.mp4');

const browser = await chromium.launch({ executablePath: process.env.CHROMIUM || undefined });
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
await page.goto('file://' + path.join(dir, 'ad.html'));
await page.waitForFunction(() => window.ready);
const total = Math.round(await page.evaluate(() => window.DURATION) * FPS);

const ff = spawn('ffmpeg', ['-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
  '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-preset', 'slow', out], { stdio: ['pipe', 'ignore', 'inherit'] });

for (let i = 0; i < total; i++) {
  const data = await page.evaluate(t => { window.draw(t); return document.getElementById('c').toDataURL('image/png'); }, i / FPS);
  if (!ff.stdin.write(Buffer.from(data.split(',')[1], 'base64'))) await new Promise(r => ff.stdin.once('drain', r));
}
ff.stdin.end();
await new Promise(r => ff.on('close', r));
await browser.close();
console.log('frames:', total, '→', out);
