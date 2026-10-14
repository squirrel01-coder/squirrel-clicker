"""Озвучка через Silero TTS v4 (snakers4/silero-models), те же реплики, что в voice.py.
Запуск: SPEAKER=eugene python3 voice_silero.py <путь к v4_ru.pt>"""
import json, os, sys, wave
import torch

SR = 48000
LINES = [x["text"] for x in json.load(open("out/timeline.json"))]
LINES = [t.replace("Некстин", "Н+екстин").replace("вотсапе", "вотс+апе").replace("си ар эм", "си-ар-+эм") for t in LINES]
model = torch.package.PackageImporter(sys.argv[1]).load_pickle("tts_models", "model")
timeline = []
for i, text in enumerate(LINES):
    audio = model.apply_tts(text=text, speaker=os.environ.get("SPEAKER", "eugene"), sample_rate=SR, put_accent=True, put_yo=True)
    with wave.open(f"out/vo_{i:02d}.wav", "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((audio.clamp(-1, 1) * 32767).short().numpy().tobytes())
    timeline.append({"i": i, "text": text, "dur": round(len(audio) / SR, 3)})
    print(i, timeline[-1]["dur"])
json.dump(timeline, open("out/timeline.json", "w"), ensure_ascii=False, indent=1)
