"""Тайминг реплик + видеофон из клипов Mixkit (кроп 9:16, лёгкий наезд/панорама, яркая цветокоррекция).
Пишет timeline.json и bg.mp4. Клипы лежат в CLIPS (скачаны с assets.mixkit.co)."""
import json, subprocess, wave, os
CLIPS = os.environ.get("CLIPS", "/tmp/nx/clips")
LEAD, GAP, TAIL = 0.4, 0.25, 3.2
# реплика -> (клип, начало в клипе, центр кадра по X 0..1, направление панорамы)
PLAN = [(4915, 2, .62, -1), (4801, 2, .38, 1), (42664, 1, .45, -1), (4919, 2, .50, 1), (4809, 5, .50, -1),
        (42648, .5, .45, 1), (4801, 9, .40, -1), (30012, .5, .60, 1), (41541, 3, .50, 1)]
tl = json.load(open("vo/timeline.json"))
t, lines = LEAD, []
for x in tl:
    with wave.open(x["file"]) as w: d = w.getnframes() / w.getframerate()
    lines.append([round(t, 3), round(t + d, 3), x["text"].replace("Нэкстин", "Nextin")]); t += d + GAP
DUR = t - GAP + TAIL
starts = [0] + [l[0] - .12 for l in lines[1:]] + [DUR]
segs = []
for i, (cid, ss, cx, dirn) in enumerate(PLAN):
    d = starts[i + 1] - starts[i]
    # источник 1920x1080 -> высота 2074 (запас 8% на движение), кроп 1080x1920 с медленной панорамой
    vf = (f"scale=-2:2074,crop=1080:1920:x='min(max(0\\,{cx}*iw-540+{dirn}*t*28)\\,iw-1080)':y='(ih-1920)/2+{dirn}*t*8',"
          f"eq=saturation=1.28:contrast=1.07:brightness=0.03,fps=30,format=yuv420p")
    out = f"seg{i}.mp4"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", str(ss), "-t", f"{d:.3f}", "-i", f"{CLIPS}/{cid}.mp4",
                    "-vf", vf, "-an", "-c:v", "libx264", "-crf", "16", "-preset", "fast", out], check=True)
    segs.append(out)
open("segs.txt", "w").write("".join(f"file '{s}'\n" for s in segs))
subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", "segs.txt", "-c", "copy", "bg.mp4"], check=True)
for s in segs: os.remove(s)
json.dump({"duration": round(DUR, 3), "lines": lines, "cuts": [round(s, 3) for s in starts[1:-1]]}, open("timeline.json", "w"), ensure_ascii=False, indent=1)
print("duration", round(DUR, 2)); [print(l) for l in lines]
