#!/usr/bin/env python3
"""Озвучка текста через Azure Speech REST API. Ключ подставляет прокси облачной среды (секрет «Azure Speech»)."""
import argparse, json, os, sys, time, urllib.request, urllib.error, wave, io
from xml.sax.saxutils import escape

def endpoint(region, path):
    return f"https://{region}.tts.speech.microsoft.com/cognitiveservices/{path}"

def request(url, data=None, headers=None, tries=5):
    for i in range(tries):
        req = urllib.request.Request(url, data=data, headers={"User-Agent": "nextin-tts", **(headers or {})})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < tries - 1:
                time.sleep(4 * (i + 1)); continue
            sys.exit(f"Azure TTS: HTTP {e.code} {e.read()[:300]!r}")

def ssml(text, voice, rate, pitch, style):
    lang = "-".join(voice.split("-")[:2])
    body = text if "<" in text else escape(text)
    inner = f'<prosody rate="{rate}" pitch="{pitch}">{body}</prosody>'
    if style:
        inner = f'<mstts:express-as style="{style}">{inner}</mstts:express-as>'
    return (f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
            f'xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="{lang}">'
            f'<voice name="{voice}">{inner}</voice></speak>').encode("utf-8")

def synth(text, a, fmt):
    return request(endpoint(a.region, "v1"), ssml(text, a.voice, a.rate, a.pitch, a.style),
                   {"Content-Type": "application/ssml+xml", "X-Microsoft-OutputFormat": fmt})

def main():
    p = argparse.ArgumentParser()
    p.add_argument("text", nargs="?")
    p.add_argument("-o", "--out", default="voice.mp3")
    p.add_argument("--lines", help="файл: одна фраза на строку -> отдельные WAV + timeline.json")
    p.add_argument("--outdir", default="vo")
    p.add_argument("--voice", default="ru-RU-DmitryNeural")
    p.add_argument("--rate", default="+0%")
    p.add_argument("--pitch", default="+0%")
    p.add_argument("--style", default="")
    p.add_argument("--region", default=os.environ.get("AZURE_SPEECH_REGION", "swedencentral"))
    p.add_argument("--list", metavar="LOCALE", help="показать голоса, например ru-RU")
    a = p.parse_args()

    if a.list:
        for v in json.loads(request(endpoint(a.region, "voices/list"))):
            if v["Locale"].startswith(a.list):
                print(v["ShortName"], v["Gender"], ",".join(v.get("StyleList", [])))
        return
    if a.lines:
        os.makedirs(a.outdir, exist_ok=True)
        lines = [l.strip() for l in open(a.lines, encoding="utf-8") if l.strip()]
        timeline = []
        for i, line in enumerate(lines):
            raw = synth(line, a, "riff-48khz-16bit-mono-pcm")
            path = os.path.join(a.outdir, f"vo_{i:02d}.wav")
            open(path, "wb").write(raw)
            with wave.open(io.BytesIO(raw)) as w:
                dur = w.getnframes() / w.getframerate()
            timeline.append({"i": i, "text": line, "file": path, "dur": round(dur, 3)})
            print(f"{i:02d} {dur:5.2f}s {line[:60]}")
        json.dump(timeline, open(os.path.join(a.outdir, "timeline.json"), "w"), ensure_ascii=False, indent=1)
        return
    if not a.text:
        p.error("нужен текст или --lines")
    fmt = "riff-48khz-16bit-mono-pcm" if a.out.endswith(".wav") else "audio-48khz-192kbitrate-mono-mp3"
    open(a.out, "wb").write(synth(a.text, a, fmt))
    print("saved", a.out)

if __name__ == "__main__":
    main()
