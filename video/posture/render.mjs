// Рендер ad.html → кадры → MP4 с озвучкой. Запуск из video/nextin: node render.mjs [кадр,...] для превью
import { createRequire } from 'node:module';
import { spawn, execSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const require = createRequire(import.meta.url);
let chromium; try { ({ chromium } = require('playwright')); } catch { ({ chromium } = require(execSync('npm root -g').toString().trim() + '/playwright')); }
const dir = path.dirname(fileURLToPath(import.meta.url)), FPS = 30;
const data = JSON.parse(readFileSync(path.join(dir, 'timeline.json'), 'utf8'));
const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
page.on('pageerror', e => console.log('ERR', e.message)); await page.goto('http://localhost:8765/ad.html');
await page.waitForFunction(() => window.ready);
const dur = await page.evaluate(d => window.setup(d), data);
const grab = t => page.evaluate(t => { window.draw(t); return document.getElementById('c').toDataURL('image/png'); }, t);
const previews = process.argv.slice(2).map(Number);
if (previews.length) {
  const fs = await import('node:fs');
  for (const t of previews) fs.writeFileSync(path.join(dir, `prev_${t}.png`), Buffer.from((await grab(t)).split(',')[1], 'base64'));
} else {
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
    '-i', path.join(dir, 'mix.wav'), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '22', '-preset', 'medium',
    '-c:a', 'aac', '-b:a', '192k', '-ac', '2', '-shortest', '-movflags', '+faststart', path.join(dir, 'rovnaya-spina.mp4')], { stdio: ['pipe', 'inherit', 'inherit'] });
  const total = Math.round(dur * FPS);
  for (let i = 0; i < total; i++) { if (!ff.stdin.write(Buffer.from((await grab(i / FPS)).split(',')[1], 'base64'))) await new Promise(r => ff.stdin.once('drain', r)); }
  ff.stdin.end(); await new Promise(r => ff.on('close', r)); console.log('frames', total);
}
await browser.close();
