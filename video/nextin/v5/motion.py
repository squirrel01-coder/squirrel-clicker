"""Детектор движения по bg.mp4 (разница кадров, OpenCV): рамка вокруг движущейся области -> motion.json;
скриншоты моментов -> shot_N.png для галереи в чате."""
import cv2, json
d = json.load(open("timeline.json")); cuts = [0] + d["cuts"] + [d["duration"]]
SCENES = [3, 4]
cap = cv2.VideoCapture("bg.mp4"); fps = cap.get(cv2.CAP_PROP_FPS)
boxes, prev, sm, i = {}, None, None, 0
SHOTS = {cuts[3] + 1.6: "shot_0.png", cuts[4] + 1.0: "shot_1.png", cuts[7] + 3.2: "shot_2.png"}
while True:
    ok, fr = cap.read()
    if not ok: break
    t = i / fps
    for ts, name in SHOTS.items():
        if abs(t - ts) < .5 / fps: cv2.imwrite(name, cv2.resize(fr, (360, 640)))
    if any(cuts[s] <= t < cuts[s + 1] for s in SCENES):
        g = cv2.GaussianBlur(cv2.cvtColor(cv2.resize(fr, (270, 480)), cv2.COLOR_BGR2GRAY), (9, 9), 0)
        if prev is not None and prev.shape == g.shape:
            m = cv2.dilate(cv2.threshold(cv2.absdiff(prev, g), 18, 255, cv2.THRESH_BINARY)[1], None, iterations=6)
            cs = [c for c in cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0] if cv2.contourArea(c) > 1500]
            if cs:
                x, y, w, h = cv2.boundingRect(max(cs, key=cv2.contourArea)); b = [x * 4, y * 4, w * 4, h * 4]
                if w * h > .35 * 270 * 480 or w * h < .02 * 270 * 480: prev = g; i += 1; continue
                sm = b if sm is None else [int(.75 * a + .25 * c) for a, c in zip(sm, b)]
                boxes[i] = [sm]
        prev = g
    else:
        prev, sm = None, None
    i += 1
json.dump({"fps": fps, "boxes": boxes}, open("motion.json", "w"))
print("frames with motion:", len(boxes))
