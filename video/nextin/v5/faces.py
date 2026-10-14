"""Находит лица в bg.mp4 (OpenCV, каскад Хаара) в нужных сценах: рамки по кадрам -> faces.json,
лучшие кадры лиц -> face_N.png для галереи «фото лиц»."""
import cv2, json
d = json.load(open("timeline.json")); cuts = [0] + d["cuts"] + [d["duration"]]
SCENES = {3: "door", 4: "entry", 6: "kids"}          # номера сцен с распознаванием
cas = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_alt2.xml")
cap = cv2.VideoCapture("bg.mp4"); fps = cap.get(cv2.CAP_PROP_FPS)
boxes, best, i = {}, {}, 0
while True:
    ok, fr = cap.read()
    if not ok: break
    t = i / fps; sc = next((s for s in SCENES if cuts[s] <= t < cuts[s + 1]), None)
    if sc is not None:
        g = cv2.cvtColor(cv2.resize(fr, (540, 960)), cv2.COLOR_BGR2GRAY)
        found = cas.detectMultiScale(g, 1.1, 6, minSize=(40, 40))
        boxes[i] = [[int(v * 2) for v in b] for b in found]
        for (x, y, w, h) in found:
            if w > best.get(sc, (0,))[0]:
                X, Y, W, H = [int(v * 2) for v in (x, y, w, h)]; pad = int(W * .35)
                best[sc] = (w, fr[max(0, Y - pad):Y + H + pad, max(0, X - pad):X + W + pad].copy(), round(t, 2))
    i += 1
json.dump({"fps": fps, "boxes": boxes}, open("faces.json", "w"))
for k, (sc, (w, crop, t)) in enumerate(sorted(best.items())):
    cv2.imwrite(f"face_{k}.png", cv2.resize(crop, (300, 300))); print("face", k, SCENES[sc], "t", t, "w", w)
print("frames with faces:", sum(1 for v in boxes.values() if v), "/", len(boxes))
