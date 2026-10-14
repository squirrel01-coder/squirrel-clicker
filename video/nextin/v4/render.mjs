// Рендер: прозрачная графика overlay.html поверх bg.mp4 + mix.wav -> nextin-live.mp4. Аргументы-секунды = превью PNG.
import { createRequire } from 'node:module';
import { spawn, execSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const require = createRequire(import.meta.url);
let chromium; try { ({ chromium } = require('playwright')); } catch { ({ chromium } = require(execSync('npm root -g').toString().trim() + '/playwright')); }
const dir = path.dirname(fileURLToPath(import.meta.url)), FPS = 30;
const data = JSON.parse(readFileSync(path.join(dir, 'timeline.json'), 'utf8'));
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1080, height: 1920 } });
await page.goto('file://' + path.join(dir, 'overlay.html'));
await page.waitForFunction(() => window.ready);
const dur = await page.evaluate(d => window.setup(d), data);
const grab = t => page.evaluate(t => { window.draw(t); return document.getElementById('c').toDataURL('image/png'); }, t);
const prev = process.argv.slice(2).map(Number);
if (prev.length) {
  for (const t of prev) {
    writeFileSync(path.join(dir, `ov_${t}.png`), Buffer.from((await grab(t)).split(',')[1], 'base64'));
    execSync(`ffmpeg -loglevel error -y -ss ${t} -i bg.mp4 -i ov_${t}.png -filter_complex "[0:v][1:v]overlay" -frames:v 1 prev_${t}.png`, { cwd: dir });
  }
} else {
  const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-i', path.join(dir, 'bg.mp4'), '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'png', '-i', '-',
    '-i', path.join(dir, 'mix.wav'), '-filter_complex', '[0:v][1:v]overlay=format=auto,format=yuv420p[v]', '-map', '[v]', '-map', '2:a',
    '-c:v', 'libx264', '-crf', '21', '-maxrate', '5M', '-bufsize', '10M', '-preset', 'medium', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart',
    path.join(dir, 'nextin-live.mp4')], { stdio: ['pipe', 'inherit', 'inherit'] });
  const total = Math.round(dur * FPS);
  for (let i = 0; i < total; i++) { if (!ff.stdin.write(Buffer.from((await grab(i / FPS)).split(',')[1], 'base64'))) await new Promise(r => ff.stdin.once('drain', r)); }
  ff.stdin.end(); await new Promise(r => ff.on('close', r)); console.log('frames', total);
}
await browser.close();
