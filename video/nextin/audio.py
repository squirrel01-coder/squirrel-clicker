"""Склеивает реплики с паузами, кладёт под голос музыку с приглушением. Пишет out/voice.wav, out/mix.wav, out/scenes.json."""
import json, wave
import numpy as np

SR = 48000
LEAD, GAP, TAIL = 0.4, 0.45, 3.0
tl = json.load(open("out/timeline.json"))

def read(path):
    with wave.open(path) as w:
        a = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
        sr = w.getframerate()
    if sr != SR:
        a = np.interp(np.arange(0, len(a), sr / SR), np.arange(len(a)), a)
    return a

t, parts, scenes = LEAD, [], []
for x in tl:
    a = read(f"out/vo_{x['i']:02d}.wav")
    a = a / (np.abs(a).max() + 1e-9) * 0.9
    scenes.append({"start": round(t, 3), "end": round(t + len(a) / SR, 3), "text": x["text"].replace("+", "")})
    parts.append((t, a))
    t += len(a) / SR + GAP
total = t - GAP + TAIL
n = int(total * SR)
voice = np.zeros(n, np.float32)
for start, a in parts:
    i = int(start * SR); voice[i:i + len(a)] += a

# Музыка: мягкий электронный бит 110 BPM, аккорды Am-F-C-G
rng = np.random.default_rng(3)
tt = np.arange(n) / SR
beat = 60 / 110
music = np.zeros(n, np.float32)
def add(sig, s):
    i = int(s * SR); seg = sig[: max(0, n - i)]; music[i:i + len(seg)] += seg
def env(L, a=0.01, d=0.3):
    x = np.arange(int(L * SR)) / SR; return np.minimum(x / a, 1) * np.exp(-x / d)
def tone(f, L, v, d):
    x = np.arange(int(L * SR)) / SR
    return sum(np.sin(2 * np.pi * f * k * x) / k ** 1.5 for k in range(1, 4)) * env(L, 0.03, d) * v
chords = [(220.0, 261.6, 329.6), (174.6, 220.0, 261.6), (130.8, 164.8, 196.0), (196.0, 246.9, 293.7)]
bar = 4 * beat
for b in range(int(total / bar) + 1):
    ch = chords[b % 4]
    for f in ch: add(tone(f, bar, 0.05, 2.0), b * bar)
    for k in range(8): add(tone(ch[0] / 2, beat / 2, 0.10, 0.15), b * bar + k * beat / 2)
for i in range(int(total / beat)):
    s = i * beat
    x = np.arange(int(0.3 * SR)) / SR
    kick = np.sin(2 * np.pi * np.cumsum(50 + 90 * np.exp(-x * 30)) / SR) * np.exp(-x * 10)
    if s > scenes[1]["start"] - 0.1: add(kick * 0.5, s)
    add(rng.standard_normal(int(0.05 * SR)) * env(0.05, 0.001, 0.012) * 0.12, s + beat / 2)
# Приглушение музыки под голосом
venv = np.convolve(np.abs(voice), np.ones(int(0.25 * SR)) / (0.25 * SR), "same")
duck = 1 - 0.65 * np.clip(venv / 0.08, 0, 1)
music *= duck * np.minimum(1, tt / 1.0) * np.minimum(1, (total - tt) / 2.0)
mix = voice * 1.0 + music * 0.55
mix = np.tanh(mix * 1.1) * 0.95
def write(p, a):
    with wave.open(p, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(a, -1, 1) * 32767).astype("<i2").tobytes())
write("out/mix.wav", mix)
json.dump({"duration": round(total, 3), "scenes": scenes}, open("out/scenes.json", "w"), ensure_ascii=False, indent=1)
print("duration", round(total, 2)); [print(s["start"], s["end"]) for s in scenes]
