"""Синтез фоновой музыки для ролика (без лицензионных ограничений): 120 BPM, 18 с → out/music.wav."""
import wave
import numpy as np

SR, DUR, BPM = 44100, 18.0, 120
BEAT = 60 / BPM
n = int(SR * DUR)
t = np.arange(n) / SR
mix = np.zeros(n)
rng = np.random.default_rng(7)


def add(sig, start):
    i = int(start * SR)
    seg = sig[: max(0, n - i)]
    mix[i : i + len(seg)] += seg


def env(length, attack=0.005, decay=0.2):
    tt = np.arange(int(length * SR)) / SR
    return np.minimum(tt / attack, 1) * np.exp(-tt / decay)


def kick():
    tt = np.arange(int(0.35 * SR)) / SR
    freq = 50 + 110 * np.exp(-tt * 30)
    return np.sin(2 * np.pi * np.cumsum(freq) / SR) * np.exp(-tt * 9)


def hat():
    return rng.standard_normal(int(0.06 * SR)) * env(0.06, 0.001, 0.015) * 0.25


def note(f, length, vol, decay):
    tt = np.arange(int(length * SR)) / SR
    saw = sum(np.sin(2 * np.pi * f * k * tt) / k for k in range(1, 6))
    return saw * env(length, 0.02, decay) * vol


def whoosh(length=0.6):
    s = np.convolve(rng.standard_normal(int(length * SR)), np.ones(30) / 30, "same")
    tt = np.linspace(0, 1, len(s))
    return s * np.sin(np.pi * tt) ** 2 * 0.35


# Am – F – C – G, по 2 такта
chords = [(220.0, 261.6, 329.6), (174.6, 220.0, 261.6), (130.8, 164.8, 196.0), (196.0, 246.9, 293.7)]
bars = int(DUR / (4 * BEAT))
for b in range(bars):
    ch = chords[(b // 2) % 4]
    start = b * 4 * BEAT
    for f in ch:  # пэд
        add(note(f, 4 * BEAT, 0.05, 1.5), start)
    for k in range(8):  # бас восьмыми
        if start + k * BEAT / 2 >= 3.0:
            add(note(ch[0] / 2, BEAT / 2, 0.12, 0.12), start + k * BEAT / 2)

for i in range(int(DUR / BEAT)):
    T = i * BEAT
    if T < 3.0:  # хук: только тиканье
        add(hat() * 1.5, T)
        continue
    if 6.0 <= T < 6.3 or T >= 17.0:
        continue  # пауза перед «решением» и в финале
    add(kick() * 0.7, T)
    add(hat(), T + BEAT / 2)

for T in (3.1, 6.3, 11.3, 14.7):
    add(whoosh(), T - 0.4)

mix *= np.minimum(1, (DUR - t) / 1.5)  # затухание в конце
mix = np.tanh(mix * 1.2) * 0.8
with wave.open("out/music.wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("ok")
