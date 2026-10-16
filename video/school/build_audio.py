"""Раскладывает реплики по сценам, синтезирует музыку и эффекты. Пишет mix.wav и timeline.json для ad.html."""
import json, wave
import numpy as np

SR = 48000
LEAD, GAP, CHAP_GAP, TAIL = 0.6, 0.32, 0.9, 3.5
# Сцена -> индексы реплик
SCENES = [("hook", [0, 1, 2, 3, 4]), ("hemis", [5, 6]), ("bot", [7, 8, 9]), ("kinder", [10, 11, 12]), ("school", [13, 14, 15]),
          ("camIntro", [16, 17]), ("camChat", [18, 19]), ("camAlert", [20, 21]), ("camClip", [22, 23]), ("dash", [24, 25, 26]), ("final", [27, 28, 29])]
tl = json.load(open("vo/timeline.json"))

def read(path):
    with wave.open(path) as w:
        return np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768

t, clips, phrases, scenes = LEAD, [], [], []
for si, (sid, idx) in enumerate(SCENES):
    if si: t += CHAP_GAP
    s0 = t
    for k, i in enumerate(idx):
        if k: t += GAP
        a = read(tl[i]["file"]); clips.append((t, a))
        disp = tl[i]["text"].replace("Хемис", "HEMIS").replace("Эксель", "Excel").replace("Ворде", "Word")
        phrases.append([round(t, 3), round(t + len(a) / SR, 3), disp, sid])
        t += len(a) / SR
    scenes.append({"id": sid, "start": round(s0 - (0 if si == 0 else CHAP_GAP * .5), 3), "lines": [p[0] for p in phrases[-len(idx):]]})
for i, s in enumerate(scenes):
    s["end"] = scenes[i + 1]["start"] if i + 1 < len(scenes) else round(t + TAIL, 3)
scenes[0]["start"] = 0
DUR = t + TAIL
n = int(DUR * SR)
voice = np.zeros(n, np.float32)
for s, a in clips:
    i = int(s * SR); voice[i:i + len(a)] += a[: n - i]
voice /= np.abs(voice).max() + 1e-9; voice *= .95

rng = np.random.default_rng(5)
music = np.zeros(n, np.float32); sfx = np.zeros(n, np.float32)
def add(buf, sig, s, g=1.0):
    i = int(s * SR)
    if i >= n: return
    seg = sig[: n - i]; buf[i:i + len(seg)] += seg * g
def tt(L): return np.arange(int(L * SR)) / SR
def env(L, a=.005, d=.2): x = tt(L); return np.minimum(x / a, 1) * np.exp(-x / d)
def saw(f, L): x = tt(L); return sum(np.sin(2 * np.pi * f * k * x) / k for k in range(1, 7))
def lp(s, k=8): return np.convolve(s, np.ones(k) / k, "same")
kick = lambda: np.sin(2 * np.pi * np.cumsum(45 + 120 * np.exp(-tt(.35) * 28)) / SR) * np.exp(-tt(.35) * 9)
clap = lambda: lp(rng.standard_normal(int(.2 * SR)), 3) * env(.2, .001, .05)
hat = lambda: np.diff(rng.standard_normal(int(.05 * SR) + 1)) * env(.05, .001, .01)
BPM = 100; B = 60 / BPM
prog = [(130.8, [261.6, 329.6, 392.0]), (110.0, [220.0, 261.6, 329.6]), (87.3, [174.6, 220.0, 261.6]), (98.0, [196.0, 246.9, 293.7])]
sc = {s["id"]: s for s in scenes}
for i in range(int(DUR / B) + 1):
    s = i * B; root, ch = prog[(i // 4) % 4]
    if i % 4 == 0:
        for f in ch: add(music, lp(saw(f, 4 * B), 16) * env(4 * B, .6, 5) * .02, s)
        add(music, lp(saw(root / 2, 4 * B), 20) * env(4 * B, .3, 3) * .05, s)
    arp = ch + [ch[1] * 2]
    for k in range(2): add(music, np.sin(2 * np.pi * arp[(i * 2 + k) % 4] * 2 * tt(B / 2)) * env(B / 2, .003, .25) * .05, s + k * B / 2)
    if s > sc["hemis"]["start"]:
        add(music, hat() * .1, s + B / 2)
        if i % 2 == 0: add(music, kick() * .22, s)
    elif i % 4 == 0: add(music, kick() * .25, s); add(music, kick() * .15, s + B * .5)
def whoosh(L=.6):
    s = lp(rng.standard_normal(int(L * SR)), 12); x = np.linspace(0, 1, len(s)); return s * np.sin(np.pi * x) ** 2 * .45
def riser(L=1.0):
    x = tt(L); return (lp(rng.standard_normal(len(x)), 4) * .2 + np.sin(2 * np.pi * np.cumsum(300 + 1500 * x / L) / SR) * .07) * (x / L) ** 2
def impact():
    x = tt(1.2); return (np.sin(2 * np.pi * np.cumsum(70 * np.exp(-x * 2) + 30) / SR) * np.exp(-x * 3) + lp(rng.standard_normal(len(x)), 6) * np.exp(-x * 12) * .4) * .8
def ping(f=1320, L=.35): x = tt(L); return (np.sin(2 * np.pi * f * x) + .5 * np.sin(2 * np.pi * f * 1.5 * x)) * np.exp(-x * 14) * .22
def pop(): x = tt(.12); return np.sin(2 * np.pi * np.cumsum(900 - 500 * x / .12) / SR) * np.exp(-x * 40) * .3
for s in scenes[1:]: add(sfx, whoosh(), s["start"] - .25, .45)
add(sfx, impact(), sc["hemis"]["start"] + .1, .5)
add(sfx, impact(), sc["camIntro"]["start"] + .1, .5)
for k in range(3): add(sfx, ping(1760, .3), sc["camAlert"]["lines"][0] + 1.6 + k * .25, .5)
add(sfx, ping(1100, .4), sc["camAlert"]["lines"][1] + 2.2, .6)
add(sfx, ping(1320, .4), sc["dash"]["lines"][2] + 1.0, .6)
add(sfx, impact(), sc["final"]["start"] + .1, .45)
x = np.arange(n) / SR
venv = np.convolve(np.abs(voice), np.ones(int(.2 * SR)) / (.2 * SR), "same")
music *= (1 - .55 * np.clip(venv / .06, 0, 1)) * np.minimum(1, x / 2) * np.minimum(1, (DUR - x) / 3)
mix = np.tanh((voice + music * .9 + sfx * .6) * 1.05)
with wave.open("mix.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(np.stack([mix, mix], 1), -1, 1) * 32767).astype("<i2").tobytes())
json.dump({"duration": round(DUR, 3), "phrases": phrases, "scenes": scenes}, open("timeline.json", "w"), ensure_ascii=False, indent=1)
print("duration", round(DUR, 1)); [print(s["id"], s["start"], s["end"]) for s in scenes]
