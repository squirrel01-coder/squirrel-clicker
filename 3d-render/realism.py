"""Фотореалистичный рендер дома по чертежам.
Сначала скрипт модели (blender_uy.py) строит геометрию строго по geom.py,
потом этот модуль заменяет материалы на фото-текстуры (Poly Haven, CC0),
ставит настоящее небо, вечернее солнце, модели деревьев, шторы и свет в окнах,
камеры «как у архитектурного фотографа» и рендерит.

Запуск:
  python realism.py <скрипт_модели.py> <папка_с_geom.py> <папка_ассетов> <папка_вывода> <test|final> <виды через запятую|all>
"""
import sys, os, math, random, runpy
script, SK, ASSETS, OUT, QUALITY, VIEWS = sys.argv[1:7]
sys.argv = [script, "--", SK, OUT + "/_model", "final", "none"]   # модель с плотной травой, без рендера
runpy.run_path(script, run_name="__main__")

import bpy
from mathutils import Vector
sys.path.insert(0, SK)
from geom import *

sc = bpy.context.scene
M = 0.001
random.seed(7)
TEX = os.path.join(ASSETS, "tex")

# ------------------------------------------------------------------ материалы
def tex_img(nt, path, noncolor, vec, proj="BOX"):
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(path, check_existing=True)
    if noncolor:
        t.image.colorspace_settings.name = "Non-Color"
    t.projection = proj
    if proj == "BOX":
        t.projection_blend = 0.25
    nt.links.new(vec, t.inputs["Vector"])
    return t

TEXSIZE = {}
def pbr(mat, tex, size_m, tint=(1, 1, 1), rough_mul=1.0, bump=1.0, rot_deg=0.0, sat=1.0, val=1.0, metal=None):
    """Перестроить материал: фото-текстура tex размером size_m метров на один повтор."""
    TEXSIZE[mat.name] = (tex, size_m, tint, sat, val, rot_deg)
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type not in ("OUTPUT_MATERIAL", "BSDF_PRINCIPLED"):
            nt.nodes.remove(n)
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    s = 1.0 / size_m
    mp.inputs["Scale"].default_value = (s, s, s)
    mp.inputs["Rotation"].default_value = (0, 0, math.radians(rot_deg))
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    v = mp.outputs["Vector"]
    d = os.path.join(TEX, tex)
    fn = lambda k: next((os.path.join(d, f) for f in os.listdir(d) if f.startswith(k + ".")), None)
    diff = tex_img(nt, fn("diff"), False, v)
    hsv = nt.nodes.new("ShaderNodeHueSaturation")
    hsv.inputs["Saturation"].default_value = sat; hsv.inputs["Value"].default_value = val
    nt.links.new(diff.outputs["Color"], hsv.inputs["Color"])
    mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"; mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 1.0
    nt.links.new(hsv.outputs["Color"], mix.inputs[6]); mix.inputs[7].default_value = (*tint, 1)
    nt.links.new(mix.outputs[2], b.inputs["Base Color"])
    if fn("rough"):
        r = tex_img(nt, fn("rough"), True, v)
        mth = nt.nodes.new("ShaderNodeMath"); mth.operation = "MULTIPLY"; mth.inputs[1].default_value = rough_mul
        mth.use_clamp = True
        nt.links.new(r.outputs["Color"], mth.inputs[0]); nt.links.new(mth.outputs[0], b.inputs["Roughness"])
    if fn("nor"):
        n_ = tex_img(nt, fn("nor"), True, v)
        nm = nt.nodes.new("ShaderNodeNormalMap"); nm.inputs["Strength"].default_value = bump
        nt.links.new(n_.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
    if metal is not None:
        b.inputs["Metallic"].default_value = metal
    return mat

def mat(name):
    return bpy.data.materials[name]

def flat(name, color, rough, metal=0.0, coat=0.0):
    m = mat(name); nt = m.node_tree
    for n in list(nt.nodes):
        if n.type not in ("OUTPUT_MATERIAL", "BSDF_PRINCIPLED"):
            nt.nodes.remove(n)
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Coat Weight"].default_value = coat
    return m

# фасад: белая штукатурка «шуба», тёмный цоколь, профнастил
pbr(mat("Suvoq"), "white_stucco", 0.7, tint=(0.98, 0.95, 0.90), bump=4.0)
pbr(mat("Ichki devor"), "white_stucco", 1.2, tint=(0.93, 0.86, 0.76), bump=0.5)
pbr(mat("Sokol tosh"), "grey_plaster", 1.5, tint=(0.20, 0.20, 0.21), sat=0.0, bump=1.0)
def roof(m, direction):
    """Профнастил НС35: волна с шагом 200 мм вдоль ската, тёмный сине-серый металл."""
    nt = m.node_tree
    for n in list(nt.nodes):
        if n.type not in ("OUTPUT_MATERIAL", "BSDF_PRINCIPLED"): nt.nodes.remove(n)
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"); nt.links.new(b.outputs[0], out.inputs["Surface"])
    b.inputs["Base Color"].default_value = (0.20, 0.23, 0.28, 1)
    b.inputs["Metallic"].default_value = 0.55; b.inputs["Roughness"].default_value = 0.38
    tc = nt.nodes.new("ShaderNodeTexCoord")
    wv = nt.nodes.new("ShaderNodeTexWave"); wv.wave_type = "BANDS"; wv.bands_direction = direction
    wv.wave_profile = "SAW"
    wv.inputs["Scale"].default_value = 0.314 / 0.200; wv.inputs["Distortion"].default_value = 0.0
    nt.links.new(tc.outputs["Object"], wv.inputs["Vector"])
    # трапеция профиля: SAW -> треугольник -> срез вершин
    tri = nt.nodes.new("ShaderNodeMath"); tri.operation = "PINGPONG"; tri.inputs[1].default_value = 0.5
    nt.links.new(wv.outputs["Fac"], tri.inputs[0])
    clp = nt.nodes.new("ShaderNodeMapRange"); clp.inputs["From Min"].default_value = 0.1; clp.inputs["From Max"].default_value = 0.4
    nt.links.new(tri.outputs[0], clp.inputs["Value"])
    bu = nt.nodes.new("ShaderNodeBump"); bu.inputs["Strength"].default_value = 1.0; bu.inputs["Distance"].default_value = 0.035
    nt.links.new(clp.outputs["Result"], bu.inputs["Height"]); nt.links.new(bu.outputs["Normal"], b.inputs["Normal"])
    # лёгкая неоднородность (пыль, разводы)
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 0.6
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    rm = nt.nodes.new("ShaderNodeMapRange"); rm.inputs["To Min"].default_value = 0.3; rm.inputs["To Max"].default_value = 0.5
    nt.links.new(nz.outputs["Fac"], rm.inputs["Value"]); nt.links.new(rm.outputs["Result"], b.inputs["Roughness"])
roof(mat("Profnastil"), "X")
roof(mat("Profnastil Y"), "Y")
pbr(mat("Ayvon plitka"), "checkered_pavement_tiles", 1.6, tint=(1.0, 1.0, 1.0), sat=0.0, val=1.35, rough_mul=0.45, bump=0.6)
pbr(mat("Trotuar plitka"), "concrete_pavement", 2.4, tint=(0.95, 0.93, 0.90), sat=0.6, bump=1.0)
pbr(mat("Beton"), "concrete_pavement", 2.4, tint=(0.85, 0.85, 0.85), sat=0.3)
pbr(mat("Asfalt"), "asphalt_02", 4.0, tint=(0.55, 0.55, 0.58), sat=0.3)
pbr(mat("Atrof yer"), "aerial_grass_rock", 12.0, tint=(0.75, 0.85, 0.6), sat=0.9)
pbr(mat("Devor qopqog'i"), "rough_concrete", 1.0, tint=(0.55, 0.55, 0.56), sat=0.0)
flat("Karniz", (0.055, 0.05, 0.05), 0.35, 0.6)            # водосток, лобовые доски — тёмные, как в образце
flat("Metall to'q", (0.03, 0.03, 0.03), 0.35, 0.8)
flat("Eshik yog'och", (0.035, 0.032, 0.03), 0.3, coat=0.4)  # входные двери тёмные
flat("PVX rom", (0.93, 0.93, 0.92), 0.25)
flat("Ustun", (0.90, 0.90, 0.89), 0.35)
flat("Shiftlik", (0.92, 0.92, 0.91), 0.6)

# ------------------------------------------------------------------ шторы и тёплый свет в окнах
curt = bpy.data.materials.new("Parda"); curt.use_nodes = True
cb = next(n for n in curt.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
cb.inputs["Base Color"].default_value = (0.32, 0.14, 0.07, 1); cb.inputs["Roughness"].default_value = 0.9
cb.inputs["Sheen Weight"].default_value = 0.5
tul = bpy.data.materials.new("Tyul"); tul.use_nodes = True
tb = next(n for n in tul.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
tb.inputs["Base Color"].default_value = (0.95, 0.92, 0.85, 1); tb.inputs["Roughness"].default_value = 0.8
tb.inputs["Transmission Weight"].default_value = 0.6; tb.inputs["Alpha"].default_value = 0.55
glow = bpy.data.materials.new("Ichki nur"); glow.use_nodes = True
gb = next(n for n in glow.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
gb.inputs["Base Color"].default_value = (0.9, 0.7, 0.45, 1)
gb.inputs["Emission Color"].default_value = (1.0, 0.68, 0.38, 1); gb.inputs["Emission Strength"].default_value = 6.0

col_h = bpy.data.collections["Uy"]
def add_box(name, p1, p2, m):
    import bmesh
    (x1, y1, z1), (x2, y2, z2) = p1, p2
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in ((x1, y1, z1), (x2, y1, z1), (x2, y2, z1), (x1, y2, z1),
                                     (x1, y1, z2), (x2, y1, z2), (x2, y2, z2), (x1, y2, z2))]
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([vs[i] for i in f])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(m)
    o = bpy.data.objects.new(name, me); col_h.objects.link(o); return o

def side_of(r):
    if r[1] == Y0: return "S"
    if r[3] == Y1: return "N"
    if r[0] == X0: return "W"
    return "E"

for i, (r, z1, z2, mk) in enumerate(windows):
    sd = side_of(r)
    s0, s1 = ((r[0], r[2]) if sd in "SN" else (r[1], r[3]))
    w = s1 - s0
    def place(a0, a1, d0, d1, zz0, zz1, m, nm):
        # d — глубина от наружной грани стены внутрь помещения, мм
        if sd == "S": p1, p2 = (a0, Y0 + d0, zz0), (a1, Y0 + d1, zz1)
        elif sd == "N": p1, p2 = (a0, Y1 - d1, zz0), (a1, Y1 - d0, zz1)
        elif sd == "W": p1, p2 = (X0 + d0, a0, zz0), (X0 + d1, a1, zz1)
        else: p1, p2 = (X1 - d1, a0, zz0), (X1 - d0, a1, zz1)
        add_box(nm, tuple(v * M for v in p1), tuple(v * M for v in p2), m)
    top = min(z2 + 250, Z_SLAB_BOT - 20)
    cw = w * 0.28
    place(s0 - 150, s0 - 150 + cw, 520, 560, max(z1 - 300, 0), top, curt, f"Parda{i}a")      # шторы по бокам
    place(s1 + 150 - cw, s1 + 150, 520, 560, max(z1 - 300, 0), top, curt, f"Parda{i}b")
    place(s0 - 150, s1 + 150, 600, 610, max(z1 - 300, 0), top, tul, f"Tyul{i}")             # тюль
    place(s0 - 600, s1 + 600, 2600, 2620, 0, Z_SLAB_BOT, glow, f"IchkiNur{i}")               # освещённая глубина комнаты

import veg_real
veg_real.PBR = pbr
veg_real.apply(M, None, QUALITY == "final")
veg_real.neighbors(M)

# ------------------------------------------------------------------ небо и солнце
w = sc.world; w.use_nodes = True; wn = w.node_tree
for n in list(wn.nodes): wn.nodes.remove(n)
tc = wn.nodes.new("ShaderNodeTexCoord"); mp = wn.nodes.new("ShaderNodeMapping")
SKY_ROT = float(os.environ.get("SKY_ROT", "200"))
mp.inputs["Rotation"].default_value = (0, 0, math.radians(SKY_ROT))
env = wn.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(os.path.join(ASSETS, "hdri", os.environ.get("SKY", "evening_road_01_puresky_4k.exr")))
bg = wn.nodes.new("ShaderNodeBackground"); bg.inputs["Strength"].default_value = float(os.environ.get("SKY_STR", "0.9"))
wo = wn.nodes.new("ShaderNodeOutputWorld")
wn.links.new(tc.outputs["Generated"], mp.inputs["Vector"]); wn.links.new(mp.outputs["Vector"], env.inputs["Vector"])
wn.links.new(env.outputs["Color"], bg.inputs["Color"]); wn.links.new(bg.outputs["Background"], wo.inputs["Surface"])

sun = bpy.data.objects.get("Quyosh")
SUN_AZ_D = float(os.environ.get("SUN_AZ", "235"))   # азимут от севера по часовой: 235 = юго-запад, вечер
SUN_EL_D = float(os.environ.get("SUN_EL", "11"))
az, el = math.radians(SUN_AZ_D), math.radians(SUN_EL_D)
d = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))  # Y = север
sun.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
sun.data.energy = float(os.environ.get("SUN_E", "4.5")); sun.data.color = (1.0, 0.72, 0.48); sun.data.angle = math.radians(0.8)

# ------------------------------------------------------------------ деревья и кусты (модели Poly Haven)
lib = bpy.data.collections.new("_daraxtlar"); sc.collection.children.link(lib)
lib.hide_render = False
hidden_parent = bpy.data.collections.new("_kutubxona"); sc.collection.children.link(hidden_parent)
def load_model(mid, target_h):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(ASSETS, "model", mid, mid + ".gltf"))
    new = [o for o in bpy.data.objects if o not in before]
    c = bpy.data.collections.new("M_" + mid); hidden_parent.children.link(c)
    for o in new:
        for uc in list(o.users_collection): uc.objects.unlink(o)
        c.objects.link(o)
    # размер: привести высоту к target_h, основание — на ноль
    pts = [o.matrix_world @ Vector(b) for o in new if o.type == "MESH" for b in o.bound_box]
    zmin = min(p.z for p in pts); h = max(p.z for p in pts) - zmin
    cx = sum(p.x for p in pts) / len(pts); cy = sum(p.y for p in pts) / len(pts)
    k = target_h / h
    root = [o for o in new if o.parent is None]
    for o in root:
        o.location = (o.location - Vector((cx, cy, zmin))) * k
        o.scale = o.scale * k
    return c

TREES = [load_model(m, h) for m, h in (("island_tree_01", 4.3), ("island_tree_02", 4.0), ("island_tree_03", 4.0), ("tree_small_02", 3.4))]
BUSH = [load_model(m, h) for m, h in (("shrub_01", 0.9), ("shrub_02", 0.8), ("shrub_04", 0.9))]
hidden_parent.hide_render = True; hidden_parent.hide_viewport = True
for c in TREES + BUSH:
    for o in c.objects: o.hide_render = False

def instance(c, x, y, z, rot, s=1.0):
    e = bpy.data.objects.new(c.name + "_i", None); e.instance_type = "COLLECTION"; e.instance_collection = c
    e.location = (x, y, z); e.rotation_euler = (0, 0, rot); e.scale = (s, s, s); lib.objects.link(e)
    return e

zg = Z_GROUND * M
trunks = [o.location.copy() for o in bpy.data.objects if o.name.startswith("Tana")]
for o in [o for o in bpy.data.objects if o.name.split(".")[0] in ("Tana", "Toj", "Barglar")]:
    bpy.data.objects.remove(o, do_unlink=True)
# кусты (самшит, лаванда) оставлены родные — они плотнее моделей

# ------------------------------------------------------------------ камеры (двухточечная перспектива)
def cam2p(name, loc, target, lens):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = 36; cd.clip_end = 600
    co = bpy.data.objects.new(name, cd); sc.collection.objects.link(co); co.location = loc
    dx, dy, dz = (Vector(target) - Vector(loc))
    yaw = math.atan2(dy, dx)
    co.rotation_euler = (math.radians(90), 0, yaw - math.radians(90))
    hd = math.hypot(dx, dy)
    cd.shift_y = (dz / hd) * lens / 36
    return co
def cam_look(name, loc, target, lens):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.clip_end = 600
    co = bpy.data.objects.new(name, cd); sc.collection.objects.link(co); co.location = loc
    co.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return co

CAMS = {
    "1_ayvon": cam2p("K1_ayvon", (16.6, -6.2, 1.55), (6.0, -0.6, 1.9), 20),
    "2_old": cam2p("K2_old", (-2.6, -11.8, 1.6), (7.5, 0.0, 2.0), 22),
    "3_yon": cam2p("K3_yon", (20.2, -2.0, 1.6), (12.0, 7.0, 2.0), 20),
    "4_hovli": cam2p("K4_hovli", (0.5, 23.5, 1.6), (8.0, 9.0, 2.1), 22),
    "5_orqa": cam2p("K5_orqa", (-3.0, 19.0, 1.6), (8.0, 4.0, 2.1), 22),
    "6_tepa": cam_look("K6_tepa", (-15.0, -33.0, 24.0), (8.5, 5.0, -1.5), 30),
}

for i, p in enumerate(trunks):
    if any((Vector((p.x, p.y)) - Vector((c.location.x, c.location.y))).length < 9.0 for c in CAMS.values() if c.location.z < 3): continue
    instance(TREES[i % len(TREES)], p.x, p.y, zg, random.uniform(0, 6.28), random.uniform(0.85, 1.15))

# окружение: земля до горизонта и деревья за участком (для вида сверху и фона)
g = bpy.data.objects.get("Atrof yer")
if g:
    g.scale = (4.0, 4.0, 1.0)
rng = random.Random(3)
px1, py1, px2, py2 = [v * M for v in PLOT_FACT]
placed = 0
while placed < 70:
    x, y = rng.uniform(-60, 75), rng.uniform(-70, 80)
    if px1 - 3 < x < px2 + 3 and py1 - 9 < y < py2 + 3: continue        # не на участке и не на улице
    if -22.5 < y < -14.0: continue                                        # улица
    near_house = any(o.name.startswith("Qo'shni") and o.type == "MESH" and
                     (Vector((x, y)) - Vector((sum(v.co.x for v in o.data.vertices) / len(o.data.vertices),
                                               sum(v.co.y for v in o.data.vertices) / len(o.data.vertices)))).length < 9
                     for o in bpy.data.objects)
    if near_house: continue
    instance(TREES[rng.randrange(len(TREES))], x, y, zg, rng.uniform(0, 6.28), rng.uniform(0.9, 1.4)); placed += 1

# ------------------------------------------------------------------ рендер
sc.render.engine = "CYCLES"
cy = sc.cycles; cy.device = "CPU"
final = QUALITY == "final"
cy.samples = int(os.environ.get('SAMPLES', '192')) if final else 48
cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.01 if final else 0.05
cy.use_denoising = True; cy.denoiser = "OPENIMAGEDENOISE"
cy.max_bounces = 8; cy.diffuse_bounces = 4; cy.glossy_bounces = 4; cy.transmission_bounces = 8
cy.caustics_reflective = False; cy.caustics_refractive = False
cy.blur_glossy = 1.0
sc.render.resolution_x, sc.render.resolution_y = (1800, 1200) if final else (900, 600)
sc.render.resolution_percentage = 100
sc.view_settings.view_transform = "AgX"
try:
    sc.view_settings.look = "AgX - Medium High Contrast"
except TypeError:
    pass
sc.view_settings.exposure = float(os.environ.get("EXPO", "0.0"))
sc.render.image_settings.file_format = "PNG"
# лёгкое виньетирование и «фото»-отклик — в постобработке (PIL), не здесь

def post(path):
    """Фото-обработка как в образце офиса: тёплый вечерний тон, насыщенность, контраст, виньетка."""
    import numpy as np
    from PIL import Image
    im = np.asarray(Image.open(path).convert("RGB")).astype(np.float32) / 255.0
    lum = im @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    warm = np.array([1.06, 1.0, 0.90], np.float32)
    w = np.clip(lum, 0, 1)[..., None]
    im = im * (1 - w * 0.6) + im * warm * (w * 0.6)                  # тёплые света
    im = im * np.array([0.98, 1.0, 1.04], np.float32) * (1 - w) + im * w   # чуть холоднее тени
    g = (im @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None]
    im = g + (im - g) * float(os.environ.get("SAT", "1.18"))            # насыщенность
    im = 0.5 + (im - 0.5) * 1.07                                       # контраст
    from PIL import ImageFilter
    l2 = (im @ np.array([0.2126, 0.7152, 0.0722], np.float32))
    hi = np.clip((l2 - 0.78) / 0.22, 0, 1)[..., None] * im
    rad = im.shape[1] / 60
    bl = np.asarray(Image.fromarray((np.clip(hi, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(rad))).astype(np.float32) / 255
    im = im + bl * np.array([1.0, 0.85, 0.65], np.float32) * float(os.environ.get("BLOOM", "0.45"))   # свечение светлых мест
    h, w_ = im.shape[:2]; yy, xx = np.mgrid[0:h, 0:w_]
    r = np.sqrt(((xx - w_ / 2) / (w_ / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2)
    im *= (1 - 0.18 * np.clip(r - 0.6, 0, 1) ** 1.5)[..., None]          # виньетка
    Image.fromarray((np.clip(im, 0, 1) * 255 + 0.5).astype(np.uint8)).save(path)

rdir = os.path.join(OUT, "RENDER" if final else "_test"); os.makedirs(rdir, exist_ok=True)
if os.environ.get("EXPORT_FBX"):
    import fbx_export
    fbx_export.run(os.environ["EXPORT_FBX"], TEXSIZE, TEX, CAMS)
    raise SystemExit(0)
views = list(CAMS) if VIEWS == "all" else VIEWS.split(",")
for v in views:
    sc.camera = CAMS[v]
    sc.render.filepath = os.path.join(rdir, v + ".png")
    bpy.ops.render.render(write_still=True)
    post(sc.render.filepath)
    print("RENDERED", v, flush=True)
if final:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "scene.blend"), compress=True)
print("DONE")
