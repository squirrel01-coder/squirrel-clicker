"""Озвучка + энергичная музыка 124 BPM + звуковые эффекты под графику. Пишет mix.wav."""
import json, wave
import numpy as np
SR = 48000
d = json.load(open("timeline.json")); L = d["lines"]; CUTS = d["cuts"]; DUR = d["duration"]; n = int(DUR * SR)
tl = json.load(open("vo/timeline.json"))
def read(p):
    with wave.open(p) as w: return np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768
voice = np.zeros(n, np.float32)
for (s, _, _), x in zip(L, tl):
    a = read(x["file"]); i = int(s * SR); voice[i:i + len(a)] += a[: n - i]
voice = voice / (np.abs(voice).max() + 1e-9) * .95
rng = np.random.default_rng(9); music = np.zeros(n, np.float32); sfx = np.zeros(n, np.float32)
def add(b, sig, s, g=1.0):
    i = int(s * SR)
    if i >= n: return
    seg = sig[: n - i]; b[i:i + len(seg)] += seg * g
def tt(Ln): return np.arange(int(Ln * SR)) / SR
def env(Ln, a=.005, dc=.2): x = tt(Ln); return np.minimum(x / a, 1) * np.exp(-x / dc)
def saw(f, Ln): x = tt(Ln); return sum(np.sin(2 * np.pi * f * k * x) / k for k in range(1, 7))
def lp(s, k=8): return np.convolve(s, np.ones(k) / k, "same")
kick = lambda: np.sin(2 * np.pi * np.cumsum(48 + 130 * np.exp(-tt(.3) * 30)) / SR) * np.exp(-tt(.3) * 10)
clap = lambda: lp(rng.standard_normal(int(.18 * SR)), 3) * env(.18, .001, .045)
hat = lambda: np.diff(rng.standard_normal(int(.04 * SR) + 1)) * env(.04, .001, .008)
B = 60 / 124
prog = [(130.8, [261.6, 329.6, 392.0]), (98.0, [196.0, 246.9, 293.7]), (110.0, [220.0, 261.6, 329.6]), (87.3, [174.6, 220.0, 261.6])]
for i in range(int(DUR / B) + 1):
    s = i * B; root, ch = prog[(i // 4) % 4]
    add(music, kick() * .8, s)
    if i % 2: add(music, clap() * .32, s)
    for k in range(4): add(music, hat() * (.28 if k % 2 else .12), s + k * B / 4)
    for k in range(2): add(music, lp(saw(root / 2, B / 2), 6) * env(B / 2, .004, .15) * .14, s + k * B / 2)
    arp = ch + [ch[2] * 2, ch[1] * 2]
    for k in range(4): add(music, saw(arp[(i * 4 + k) % 5] * 2, B / 4) * env(B / 4, .002, .06) * .02, s + k * B / 4)
    if i % 4 == 0:
        for f in ch: add(music, lp(saw(f, 4 * B), 10) * env(4 * B, .3, 3) * .018, s)
def whoosh(Ln=.5): s = lp(rng.standard_normal(int(Ln * SR)), 10); x = np.linspace(0, 1, len(s)); return s * np.sin(np.pi * x) ** 2 * .45
def impact(): x = tt(1.0); return (np.sin(2 * np.pi * np.cumsum(70 * np.exp(-x * 2) + 30) / SR) * np.exp(-x * 3) + lp(rng.standard_normal(len(x)), 6) * np.exp(-x * 12) * .4) * .8
def ping(f=1320, Ln=.3): x = tt(Ln); return (np.sin(2 * np.pi * f * x) + .5 * np.sin(2 * np.pi * f * 1.5 * x)) * np.exp(-x * 14) * .22
def pop(): x = tt(.1); return np.sin(2 * np.pi * np.cumsum(950 - 500 * x / .1) / SR) * np.exp(-x * 40) * .3
def buzz(): x = tt(.25); return np.sign(np.sin(2 * np.pi * 160 * x)) * np.exp(-x * 10) * .08
def ding(): return ping(1568, .7) + ping(2093, .7) * .6
for c in CUTS: add(sfx, whoosh(), c - .25, .7)
a = [l[0] for l in L]
def typeclick(): return np.diff(rng.standard_normal(int(.012 * SR) + 1)) * env(.012, .0005, .003) * .25
for k in range(14): add(sfx, typeclick(), a[0] + 1.4 + k * .065)
add(sfx, pop(), a[0] + 2.3); add(sfx, impact(), a[1], .5); add(sfx, ping(1320), a[1] + .9, .8)
add(sfx, impact(), a[2], .8)
for i in range(3): add(sfx, pop(), a[2] + 3.0 + i * .5, .6)
add(sfx, pop(), a[3] + .9); add(sfx, ping(1320), a[3] + 2.8, .8); add(sfx, pop(), a[3] + 3.4); add(sfx, pop(), a[3] + 3.8)
add(sfx, pop(), a[4] + .8); add(sfx, whoosh(.8), a[4] + 1.6, .5); add(sfx, ding(), a[4] + 3.0, .7)
for i in (5, 6, 7): add(sfx, pop(), a[i] + .6); add(sfx, ping(1320), a[i] + 1.6, .7)
add(sfx, impact(), a[8], .9); add(sfx, ding(), a[8] + 1.6, .5)
x = np.arange(n) / SR
venv = np.convolve(np.abs(voice), np.ones(int(.2 * SR)) / (.2 * SR), "same")
music *= (1 - .5 * np.clip(venv / .06, 0, 1)) * np.minimum(1, x / .5) * np.minimum(1, (DUR - x) / 2.5)
mix = np.tanh((voice + music * .85 + sfx * .7) * 1.05)
with wave.open("mix.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(np.stack([mix, mix], 1), -1, 1) * 32767).astype("<i2").tobytes())
print("ok", round(DUR, 1))
