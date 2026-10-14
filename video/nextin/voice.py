"""Озвучка ролика Nextin через Piper TTS (офлайн, ONNX). Пишет out/vo_XX.wav и out/timeline.json.
Запуск: python3 voice.py <путь к ru_RU-*.onnx>"""
import json, os, sys, wave
from piper import PiperVoice, SynthesisConfig

voice = PiperVoice.load(sys.argv[1])
cfg = SynthesisConfig(length_scale=float(os.environ.get("PACE", "0.92")), noise_scale=0.6, noise_w_scale=0.7)

# Реплики по сценам; написаны «как слышится», чтобы синтез не спотыкался о латиницу и аббревиатуры.
LINES = [
    "Клиент написал вам в одиннадцать вечера. Ответили утром. А он уже купил у конкурентов.",
    "Заявки теряются. Менеджеры не успевают. Отчёты собираются вручную.",
    "Некстин внедряет умных агентов на базе искусственного интеллекта.",
    "Агент отвечает клиентам круглосуточно. В телеграме, вотсапе и на сайте. На узбекском, русском и английском.",
    "Он сам понимает, кто готов купить, и передаёт заявку в вашу си ар эм.",
    "Восемь лет опыта. Больше тридцати проектов. И месяц бесплатной поддержки после запуска.",
    "Напишите нам в директ. Бесплатно покажем, что в вашем бизнесе можно автоматизировать уже сейчас.",
]

os.makedirs("out", exist_ok=True)
timeline = []
for i, text in enumerate(LINES):
    path = f"out/vo_{i:02d}.wav"
    with wave.open(path, "wb") as w:
        voice.synthesize_wav(text, w, syn_config=cfg)
    with wave.open(path) as w:
        dur = w.getnframes() / w.getframerate()
    timeline.append({"i": i, "text": text, "dur": round(dur, 3)})
    print(i, round(dur, 2))
json.dump(timeline, open("out/timeline.json", "w"), ensure_ascii=False, indent=1)
