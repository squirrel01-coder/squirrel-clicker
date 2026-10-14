"""Звук ролика v2: озвучка + энергичная музыка (дроп после хука) + звуковые эффекты под анимацию. Пишет mix.wav."""
import json, wave
import numpy as np

SR = 48000
d = json.load(open("scenes.json"))
OFF = d["offset"]
P = [(a + OFF, b + OFF) for a, b, _ in d["phrases"]]
ps = lambda i: P[i][0]
DUR = P[-1][1] + d["tail"]
n = int(DUR * SR)
rng = np.random.default_rng(11)

def read_wav(path):
    with wave.open(path) as w:
        return np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768

voice = np.zeros(n, np.float32)
v = read_wav("voice_cut.wav"); v = v / (np.abs(v).max() + 1e-9) * 0.95
i0 = int(OFF * SR); voice[i0:i0 + len(v)] = v[: n - i0]

music = np.zeros(n, np.float32); sfx = np.zeros(n, np.float32)
def add(buf, sig, s, g=1.0):
    i = int(s * SR)
    if i >= n or i + len(sig) <= 0: return
    a = max(0, -i); seg = sig[a: max(0, n - i)]; buf[max(i, 0): max(i, 0) + len(seg)] += seg * g
def tt(L): return np.arange(int(L * SR)) / SR
def env(L, a=0.005, dcy=0.2): x = tt(L); return np.minimum(x / a, 1) * np.exp(-x / dcy)
def saw(f, L): x = tt(L); return sum(np.sin(2 * np.pi * f * k * x) / k for k in range(1, 7))
def lp(sig, k=8): return np.convolve(sig, np.ones(k) / k, "same")

BPM = 118; B = 60 / BPM; DROP = ps(2)
kick = lambda: np.sin(2 * np.pi * np.cumsum(45 + 120 * np.exp(-tt(.35) * 28)) / SR) * np.exp(-tt(.35) * 9)
clap = lambda: lp(rng.standard_normal(int(.2 * SR)), 3) * env(.2, .001, .05)
hat = lambda: np.diff(rng.standard_normal(int(.05 * SR) + 1)) * env(.05, .001, .01)
prog = [(110.0, [220.0, 261.6, 329.6]), (87.3, [174.6, 220.0, 261.6]), (130.8, [261.6, 329.6, 392.0]), (98.0, [196.0, 246.9, 293.7])]

beats = int(DUR / B) + 1
for i in range(beats):
    s = i * B; bar = i // 4; root, ch = prog[bar % 4]
    if s < DROP - .05:
        add(music, hat() * .5, s); add(music, hat() * .3, s + B / 2)          # хук: напряжённое тиканье
        if i % 4 == 0:
            for f in ch: add(music, lp(saw(f, 4 * B), 20) * env(4 * B, .5, 3) * .03, s)
        continue
    add(music, kick() * .9, s)
    if i % 2 == 1: add(music, clap() * .35, s)
    for k in range(4): add(music, hat() * (.35 if k % 2 else .18), s + k * B / 4)
    add(music, lp(saw(root / 2, B / 2), 6) * env(B / 2, .005, .18) * .16, s)        # бас
    add(music, lp(saw(root / 2, B / 2), 6) * env(B / 2, .005, .18) * .12, s + B / 2)
    arp = ch + [ch[1] * 2]
    for k in range(2): add(music, saw(arp[(i * 2 + k) % 4] * 2, B / 2) * env(B / 2, .002, .09) * .025, s + k * B / 2)  # арпеджио
    if i % 4 == 0:
        for f in ch: add(music, lp(saw(f, 4 * B), 12) * env(4 * B, .3, 4) * .022, s)

# Звуковые эффекты
def whoosh(L=.5):
    s = lp(rng.standard_normal(int(L * SR)), 12); x = np.linspace(0, 1, len(s)); return s * np.sin(np.pi * x) ** 2 * .5
def riser(L=1.0):
    x = tt(L); return (lp(rng.standard_normal(len(x)), 4) * .2 + np.sin(2 * np.pi * np.cumsum(300 + 1500 * x / L) / SR) * .08) * (x / L) ** 2
def impact():
    x = tt(1.2); return (np.sin(2 * np.pi * np.cumsum(70 * np.exp(-x * 2) + 30) / SR) * np.exp(-x * 3) + lp(rng.standard_normal(len(x)), 6) * np.exp(-x * 12) * .4) * .9
def ping(f=1320, L=.35): x = tt(L); return (np.sin(2 * np.pi * f * x) + .5 * np.sin(2 * np.pi * f * 1.5 * x)) * np.exp(-x * 14) * .25
def pop(): x = tt(.12); return np.sin(2 * np.pi * np.cumsum(900 - 500 * x / .12) / SR) * np.exp(-x * 40) * .35
def click(): return np.diff(rng.standard_normal(int(.012 * SR) + 1)) * env(.012, .0005, .003) * .25
def ding(): return ping(1568, .8) + ping(2093, .8) * .6
def ring(L=.9):
    x = tt(L); return (np.sin(2 * np.pi * 440 * x) + np.sin(2 * np.pi * 480 * x)) * (np.sin(2 * np.pi * 20 * x) > 0) * .07 * np.minimum(1, (L - x) * 8)

for i in range(10): add(sfx, ping(1200 + (i % 3) * 140), .15 + i * .42, .8)      # лавина уведомлений
add(sfx, riser(1.2), DROP - 1.2); add(sfx, impact(), DROP, .8)
cuts = [ps(3), ps(5), ps(6), ps(7), ps(8), ps(9), ps(10)]
for c in cuts: add(sfx, whoosh(), c - .3, .6)
add(sfx, pop(), ps(4) + .2)                                                       # сообщение клиента
for k in range(10): add(sfx, click(), ps(5) - .1 + k * .07)                       # бот печатает
add(sfx, pop(), ps(5) + .6); add(sfx, pop(), ps(5) + 1.5)
add(sfx, ding(), ps(5) + 2.0, .8)                                                 # заказ принят
add(sfx, whoosh(.6), ps(5) + 2.6, .7)                                             # карточка летит менеджеру
add(sfx, ring(), ps(6), 1.0)
for k in range(3): add(sfx, ping(1760, .25), ps(6) + .45 + k * .3, .5)           # галочки
add(sfx, ping(1046, .4), ps(7), .9)                                               # уведомление отчёта
for k in range(6): add(sfx, pop(), ps(8) + [0, .55, 1.6, 2.2, 2.6, 2.8][k], .7)  # плитки услуг
add(sfx, riser(.9), ps(9) - .9); add(sfx, impact(), ps(9), 1.0)                   # логотип
add(sfx, ding(), ps(10) + .8, .6)                                                 # кнопка CTA

t = np.arange(n) / SR
venv = np.convolve(np.abs(voice), np.ones(int(.2 * SR)) / (.2 * SR), "same")
duck = 1 - .5 * np.clip(venv / .06, 0, 1)
music *= duck * np.minimum(1, (DUR - t) / 2.5)
mix = voice * 1.0 + music * .8 + sfx * .7
mix = np.tanh(mix * 1.05)
st = np.stack([mix, mix], 1)
with wave.open("mix.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((np.clip(st, -1, 1) * 32767).astype("<i2").tobytes())
print("dur", round(DUR, 2))
