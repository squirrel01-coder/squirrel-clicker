"""Скачать ассеты Poly Haven (CC0): python ph_get.py <папка> hdri:<id>:<res> tex:<id>:<res> model:<id>:<res>"""
import json, os, sys, urllib.request
op = urllib.request.build_opener(); op.addheaders = [("User-Agent", "render-pipeline/1.0")]; urllib.request.install_opener(op)
out = sys.argv[1]
def get(url, path):
    if os.path.exists(path): return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    urllib.request.urlretrieve(url, path)
for spec in sys.argv[2:]:
    kind, aid, res = spec.split(":")
    f = json.load(urllib.request.urlopen(f"https://api.polyhaven.com/files/{aid}"))
    if kind == "hdri":
        u = f["hdri"][res]["exr"]["url"]; get(u, f"{out}/hdri/{aid}_{res}.exr")
    elif kind == "tex":
        for mp, key in (("Diffuse", "diff"), ("nor_gl", "nor"), ("Rough", "rough"), ("Displacement", "disp"), ("AO", "ao")):
            if mp in f and res in f[mp]:
                fmt = "jpg" if "jpg" in f[mp][res] else "png"
                get(f[mp][res][fmt]["url"], f"{out}/tex/{aid}/{key}.{fmt}")
    elif kind == "model":
        g = f["gltf"][res]["gltf"]
        get(g["url"], f"{out}/model/{aid}/{aid}.gltf")
        for rel, inc in g.get("include", {}).items():
            get(inc["url"], f"{out}/model/{aid}/{rel}")
    print("ok", spec, flush=True)
