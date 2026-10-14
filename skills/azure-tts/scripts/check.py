"""Проверка озвучки на слух: Whisper распознаёт запись, печатает текст и слова с низкой уверенностью
(кандидаты на неразборчивое или неправильное произношение). Запуск: python3 check.py medium файл.mp3 ...
Нужно: pip install faster-whisper. Ударения этим не проверить надёжно."""
import sys, subprocess, numpy as np
from faster_whisper import WhisperModel
m = WhisperModel(sys.argv[1], device="cpu", compute_type="int8")
for f in sys.argv[2:]:
    pcm = subprocess.run(['ffmpeg','-loglevel','error','-i',f,'-ac','1','-ar','16000','-f','s16le','-'],capture_output=True,check=True).stdout
    audio = np.frombuffer(pcm, np.int16).astype(np.float32) / 32768
    segs, info = m.transcribe(audio, language="ru", word_timestamps=True, beam_size=5)
    words = [w for s in segs for w in s.words]
    print(f"== {f}")
    print("".join(w.word for w in words).strip())
    print("  низкая уверенность:", [(w.word.strip(), round(w.probability, 2)) for w in words if w.probability < 0.7])
