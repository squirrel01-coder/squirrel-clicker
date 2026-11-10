"""3D-модель и рендер NAMUNA 7-UY по geom.py (тем же данным, что и чертежи).
Запуск:  blender.exe -b --factory-startup -P blender_uy.py -- <папка_скриптов> <папка_проекта> <test|final> [виды через запятую]
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
SK, OUT, MODE = argv[0], argv[1], argv[2]
VIEWS = argv[3].split(",") if len(argv) > 3 else ["front", "ayvon", "back", "aerial"]
sys.path.insert(0, SK)
from geom import *

random.seed(42)
M = 0.001   # мм -> м

# ---------------- очистка ----------------
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)
sc = bpy.context.scene
sc.unit_settings.system = "METRIC"

def coll(name, hide_render=False):
    c = bpy.data.collections.new(name)
    sc.collection.children.link(c)
    c.hide_render = hide_render
    return c
C_HOUSE, C_SITE, C_VEG, C_SRC, C_CTX = coll("Uy"), coll("Hovli"), coll("O'simliklar"), coll("_manba"), coll("Atrof")

# ---------------- материалы ----------------
def P(mat):
    return next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")

def newmat(name, color, rough=0.5, metal=0.0):
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    b = P(m)
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    m.diffuse_color = (*color, 1)
    return m

def add_bump(m, scale, strength, dist=0.02, kind="noise", direction="X", detail=8.0):
    nt = m.node_tree; b = P(m)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    if kind == "noise":
        t = nt.nodes.new("ShaderNodeTexNoise"); t.inputs["Scale"].default_value = scale
        t.inputs["Detail"].default_value = detail
        out = t.outputs["Fac"]
    else:
        t = nt.nodes.new("ShaderNodeTexWave"); t.wave_type = "BANDS"; t.bands_direction = direction
        t.inputs["Scale"].default_value = scale; t.inputs["Distortion"].default_value = 0
        out = t.outputs["Fac"]
    nt.links.new(tc.outputs["Object"], t.inputs["Vector"])
    bu = nt.nodes.new("ShaderNodeBump"); bu.inputs["Strength"].default_value = strength
    bu.inputs["Distance"].default_value = dist
    nt.links.new(out, bu.inputs["Height"]); nt.links.new(bu.outputs["Normal"], b.inputs["Normal"])
    return t

def color_var(m, c1, c2, scale=3.0, coord="Object"):
    nt = m.node_tree; b = P(m)
    tc = nt.nodes.new("ShaderNodeTexCoord"); n = nt.nodes.new("ShaderNodeTexNoise")
    n.inputs["Scale"].default_value = scale
    nt.links.new(tc.outputs[coord], n.inputs["Vector"])
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"
    mx.inputs[6].default_value = (*c1, 1); mx.inputs[7].default_value = (*c2, 1)
    nt.links.new(n.outputs["Fac"], mx.inputs[0]); nt.links.new(mx.outputs[2], b.inputs["Base Color"])
    return mx

MAT = {}
MAT["plaster"] = newmat("Suvoq", (0.86, 0.84, 0.79), 0.9); add_bump(MAT["plaster"], 220, 0.08, 0.005)
color_var(MAT["plaster"], (0.88, 0.86, 0.81), (0.80, 0.78, 0.73), 2.0)
MAT["inner"] = newmat("Ichki devor", (0.82, 0.78, 0.70), 0.9)
MAT["plinth"] = newmat("Sokol tosh", (0.16, 0.16, 0.17), 0.8); add_bump(MAT["plinth"], 25, 0.3, 0.01)
MAT["roof"] = newmat("Profnastil", (0.22, 0.24, 0.26), 0.38, 0.65)
MAT["roofY"] = MAT["roof"].copy(); MAT["roofY"].name = "Profnastil Y"
add_bump(MAT["roof"], 3.0, 0.6, 0.02, "wave", "X"); add_bump(MAT["roofY"], 3.0, 0.6, 0.02, "wave", "Y")
MAT["fascia"] = newmat("Karniz", (0.10, 0.10, 0.11), 0.5, 0.3)
MAT["soffit"] = newmat("Shiftlik", (0.85, 0.85, 0.83), 0.7)
MAT["pvc"] = newmat("PVX rom", (0.92, 0.92, 0.91), 0.35)
MAT["glass"] = newmat("Oyna", (0.9, 0.95, 0.97), 0.0)
P(MAT["glass"]).inputs["Transmission Weight"].default_value = 1.0
P(MAT["glass"]).inputs["IOR"].default_value = 1.45
MAT["door"] = newmat("Eshik yog'och", (0.20, 0.10, 0.05), 0.45); add_bump(MAT["door"], 6, 0.15, 0.01, "wave", "Z")
MAT["door_in"] = newmat("Ichki eshik", (0.55, 0.40, 0.27), 0.5)
MAT["floor"] = newmat("Laminat", (0.45, 0.30, 0.18), 0.4); add_bump(MAT["floor"], 4, 0.1, 0.005, "wave", "X")
MAT["ceil"] = newmat("Ship", (0.9, 0.9, 0.88), 0.9)
MAT["metal_dark"] = newmat("Metall to'q", (0.05, 0.05, 0.055), 0.4, 0.8)
MAT["column"] = newmat("Ustun", (0.93, 0.93, 0.92), 0.3)
MAT["concrete"] = newmat("Beton", (0.55, 0.54, 0.52), 0.85); add_bump(MAT["concrete"], 40, 0.15, 0.01)
MAT["asphalt"] = newmat("Asfalt", (0.07, 0.07, 0.075), 0.85); add_bump(MAT["asphalt"], 80, 0.3, 0.005)
MAT["line"] = newmat("Chiziq", (0.85, 0.85, 0.8), 0.6)
MAT["soil"] = newmat("Tuproq", (0.10, 0.12, 0.05), 1.0); color_var(MAT["soil"], (0.08, 0.11, 0.04), (0.16, 0.14, 0.08), 0.6)
MAT["dirt"] = newmat("Atrof yer", (0.22, 0.20, 0.15), 1.0); color_var(MAT["dirt"], (0.20, 0.19, 0.13), (0.16, 0.20, 0.10), 0.15)
MAT["bark"] = newmat("Po'stloq", (0.12, 0.08, 0.05), 0.9); add_bump(MAT["bark"], 30, 0.5, 0.02)
MAT["cap"] = newmat("Devor qopqog'i", (0.35, 0.35, 0.36), 0.6)

def tile_mat(name, c1, c2, size, rough=0.35):
    m = newmat(name, c1, rough)
    nt = m.node_tree; b = P(m)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    br = nt.nodes.new("ShaderNodeTexBrick")
    br.offset = 0.0 if "Ayvon" in name else 0.5
    br.inputs["Color1"].default_value = (*c1, 1); br.inputs["Color2"].default_value = (*c2, 1)
    br.inputs["Mortar"].default_value = (0.35, 0.35, 0.33, 1)
    br.inputs["Scale"].default_value = 1.0 / size
    br.inputs["Mortar Size"].default_value = 0.004
    br.inputs["Brick Width"].default_value = 0.5 if "Ayvon" in name else 1.0
    br.inputs["Row Height"].default_value = 0.5 if "Ayvon" in name else 0.5
    nt.links.new(tc.outputs["Object"], br.inputs["Vector"])
    nt.links.new(br.outputs["Color"], b.inputs["Base Color"])
    bu = nt.nodes.new("ShaderNodeBump"); bu.inputs["Strength"].default_value = 0.4; bu.inputs["Distance"].default_value = 0.003
    nt.links.new(br.outputs["Fac"], bu.inputs["Height"]); nt.links.new(bu.outputs["Normal"], b.inputs["Normal"])
    return m
MAT["tile"] = tile_mat("Ayvon plitka", (0.86, 0.85, 0.82), (0.30, 0.30, 0.32), 1.0, 0.25)
MAT["paver"] = tile_mat("Trotuar plitka", (0.62, 0.58, 0.52), (0.55, 0.51, 0.46), 0.5, 0.8)

def emit_mat(name, color, strength):
    m = newmat(name, color, 0.5)
    b = P(m)
    b.inputs["Emission Color"].default_value = (*color, 1)
    b.inputs["Emission Strength"].default_value = strength
    return m
MAT["lamp"] = emit_mat("Chiroq", (1.0, 0.82, 0.6), 25)

def veg_mat(name, cols, translucent=0.35):
    """Цвет по Object Info > Random (у каждого экземпляра свой оттенок)."""
    m = newmat(name, cols[0], 0.55)
    nt = m.node_tree; b = P(m)
    oi = nt.nodes.new("ShaderNodeObjectInfo")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    el = ramp.color_ramp.elements
    el[0].color = (*cols[0], 1); el[1].color = (*cols[-1], 1)
    for i, c in enumerate(cols[1:-1], 1):
        e = el.new(i / (len(cols) - 1)); e.color = (*c, 1)
    if len(cols) > 2 and name.startswith("Lavanda"):
        ramp.color_ramp.interpolation = "CONSTANT"
    nt.links.new(oi.outputs["Random"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    try:
        b.inputs["Subsurface Weight"].default_value = 0.0
    except KeyError:
        pass
    # просвечивание листвы
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    tr = nt.nodes.new("ShaderNodeBsdfTranslucent")
    nt.links.new(ramp.outputs["Color"], tr.inputs["Color"])
    mix = nt.nodes.new("ShaderNodeMixShader"); mix.inputs[0].default_value = translucent
    nt.links.new(b.outputs[0], mix.inputs[1]); nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return m
MAT["grass"] = veg_mat("O't", [(0.05, 0.16, 0.02), (0.10, 0.25, 0.03), (0.16, 0.30, 0.05), (0.22, 0.30, 0.08)], 0.3)
MAT["leaf"] = veg_mat("Barg", [(0.03, 0.09, 0.015), (0.06, 0.16, 0.03), (0.10, 0.20, 0.04), (0.14, 0.22, 0.05)], 0.4)
MAT["leaf_inner"] = newmat("Barg ichki", (0.02, 0.05, 0.01), 0.9)
MAT["lavender"] = veg_mat("Lavanda", [(0.06, 0.14, 0.04), (0.25, 0.14, 0.45), (0.30, 0.18, 0.55)], 0.3)
MAT["boxwood"] = veg_mat("Buxus", [(0.02, 0.08, 0.015), (0.04, 0.13, 0.02), (0.06, 0.17, 0.03)], 0.3)

# ---------------- геометрия ----------------
def box(name, x1, y1, z1, x2, y2, z2, mat, col=C_HOUSE, mm=True):
    k = M if mm else 1.0
    x1, y1, z1, x2, y2, z2 = [v * k for v in (x1, y1, z1, x2, y2, z2)]
    bm = bmesh.new()
    vs = [bm.verts.new(p) for p in ((x1, y1, z1), (x2, y1, z1), (x2, y2, z1), (x1, y2, z1),
                                     (x1, y1, z2), (x2, y1, z2), (x2, y2, z2), (x1, y2, z2))]
    for f in ((0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)):
        bm.faces.new([vs[i] for i in f])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); col.objects.link(ob)
    return ob

def mesh_from(name, verts, faces, mat, col):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    if mat:
        me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); col.objects.link(ob)
    return ob

def cyl(name, x, y, z1, z2, r, mat, col=C_HOUSE, verts=24):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=verts, radius1=r, radius2=r, depth=z2 - z1)
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free(); me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me); ob.location = (x, y, (z1 + z2) / 2); col.objects.link(ob)
    return ob

# ---- стены с проёмами (кусками, без булевых операций) ----
OPS = [(w[0], w[1], w[2]) for w in windows] + [(d[0], 0, d[4]) for d in doors] + [(a[0], 0, a[1]) for a in arches]
def wall_pieces(rect, zb, zt, mat, name):
    x1, y1, x2, y2 = rect
    horiz = (x2 - x1) > (y2 - y1)
    a0, a1 = (x1, x2) if horiz else (y1, y2)
    cuts = []
    for (r, z1, z2) in OPS:
        if r[0] < x2 and r[2] > x1 and r[1] < y2 and r[3] > y1:
            s0, s1 = (r[0], r[2]) if horiz else (r[1], r[3])
            cuts.append((max(s0, a0), min(s1, a1), z1, z2))
    cuts.sort()
    pcs, pos = [], a0
    for (s0, s1, z1, z2) in cuts:
        if s0 > pos:
            pcs.append((pos, s0, zb, zt))
        if z1 > zb:
            pcs.append((s0, s1, zb, z1))
        if z2 < zt:
            pcs.append((s0, s1, z2, zt))
        pos = max(pos, s1)
    if pos < a1:
        pcs.append((pos, a1, zb, zt))
    for i, (s0, s1, z1, z2) in enumerate(pcs):
        if horiz:
            box(f"{name}_{i}", s0, y1, z1, s1, y2, z2, mat)
        else:
            box(f"{name}_{i}", x1, s0, z1, x2, s1, z2, mat)

def _trim(r, ends):
    # убрать нахлёст стен в углах и примыканиях (иначе совпадающие грани дают тёмные полосы)
    x1, y1, x2, y2 = r
    if (x2 - x1) > (y2 - y1):
        return (x1 + ends, y1, x2 - ends, y2)
    return (x1, y1 + ends, x2, y2 - ends)
for i, r in enumerate(bearing):
    rr_ = r if i < 2 else _trim(r, T - 1)       # оси А и Г — целиком, остальные — между ними
    wall_pieces(rr_, 0, Z_EAVES, MAT["plaster"], f"Devor{i}")
for i, r in enumerate(partitions):
    wall_pieces(r, 0, Z_SLAB_BOT, MAT["inner"], f"Tosiq{i}")
box("Sokol", X0 - 20, Y0 - 20, Z_GROUND, X1 + 20, Y1 + 20, 0, MAT["plinth"])
box("Ship plita", X0 + 100, Y0 + 100, Z_SLAB_BOT, X1 - 100, Y1 - 100, Z_SLAB_BOT + 220, MAT["ceil"])
for n, name, code, rs in rooms:
    for j, r in enumerate(rs):
        box(f"Pol_{n}_{j}", r[0], r[1], -30, r[2], r[3], 0, MAT["floor"])

# ---- окна ----
def side_of(r):
    if r[1] == Y0: return "S"
    if r[3] == Y1: return "N"
    if r[0] == X0: return "W"
    return "E"
def wbox(name, side, s0, s1, d0, d1, z0, z1, mat):
    if side == "S":   return box(name, s0, Y0 + d0, z0, s1, Y0 + d1, z1, mat)
    if side == "N":   return box(name, s0, Y1 - d1, z0, s1, Y1 - d0, z1, mat)
    if side == "W":   return box(name, X0 + d0, s0, z0, X0 + d1, s1, z1, mat)
    return box(name, X1 - d1, s0, z0, X1 - d0, s1, z1, mat)

for i, (r, z1, z2, mk) in enumerate(windows):
    sd = side_of(r)
    s0, s1 = (r[0], r[2]) if sd in "SN" else (r[1], r[3])
    d0, d1, f = 90, 160, 65
    pv = MAT["pvc"]
    wbox(f"Rom{i}a", sd, s0, s1, d0, d1, z1, z1 + f, pv)
    wbox(f"Rom{i}b", sd, s0, s1, d0, d1, z2 - f, z2, pv)
    wbox(f"Rom{i}c", sd, s0, s0 + f, d0, d1, z1, z2, pv)
    wbox(f"Rom{i}d", sd, s1 - f, s1, d0, d1, z1, z2, pv)
    n = max(1, round((s1 - s0) / 750))
    for k_ in range(1, n):
        u = s0 + (s1 - s0) * k_ / n
        wbox(f"Rom{i}m{k_}", sd, u - 35, u + 35, d0, d1, z1, z2, pv)
    if z2 - z1 > 1000:
        wbox(f"Rom{i}t", sd, s0, s1, d0, d1, z2 - 480, z2 - 420, pv)
    wbox(f"Oyna{i}", sd, s0 + f, s1 - f, 120, 128, z1 + f, z2 - f, MAT["glass"])
    wbox(f"Otliv{i}", sd, s0 - 40, s1 + 40, -60, d0, z1 - 30, z1, MAT["fascia"])
    wbox(f"Podokon{i}", sd, s0 - 40, s1 + 40, d1, 460, z1 - 30, z1, MAT["pvc"])

# ---- двери ----
for i, ((x1, y1, x2, y2), hinge, sw, mk, h) in enumerate(doors):
    horiz = x2 - x1 > y2 - y1
    m = MAT["door"] if mk == "Д1" else MAT["door_in"]
    if horiz:
        yc = (y1 + y2) / 2 + (-100 if mk == "Д1" else 0)
        box(f"Eshik{i}", x1 + 20, yc - 25, 0, x2 - 20, yc + 25, h - 20, m)
        if mk == "Д1":
            box(f"EshikOyna{i}", x1 + 200, yc - 30, h - 900, x2 - 200, yc - 26, h - 250, MAT["glass"])
            box(f"Tutqich{i}", x2 - 160, yc - 60, 1000, x2 - 120, yc - 25, 1200, MAT["metal_dark"])
    else:
        xc = (x1 + x2) / 2
        box(f"Eshik{i}", xc - 25, y1 + 20, 0, xc + 25, y2 - 20, h - 20, m)

# ---- кровля (вальмовая) ----
x1, y1, x2, y2 = [v * M for v in ROOF]
ez, rz = Z_EAVES * M, Z_RIDGE * M
half = (y2 - y1) / 2
rl, rr, ym = x1 + half, x2 - half, (y1 + y2) / 2
faces = {"S": ([(x1, y1, ez), (x2, y1, ez), (rr, ym, rz), (rl, ym, rz)], "roof"),
         "N": ([(x2, y2, ez), (x1, y2, ez), (rl, ym, rz), (rr, ym, rz)], "roof"),
         "W": ([(x1, y2, ez), (x1, y1, ez), (rl, ym, rz)], "roofY"),
         "E": ([(x2, y1, ez), (x2, y2, ez), (rr, ym, rz)], "roofY")}
for k_, (vs, mk) in faces.items():
    ob = mesh_from(f"Tom_{k_}", vs, [list(range(len(vs)))], MAT[mk], C_HOUSE)
    sol = ob.modifiers.new("qalinlik", "SOLIDIFY"); sol.thickness = 0.04; sol.offset = 1
box("Karniz osti", ROOF[0], ROOF[1], Z_EAVES - 60, ROOF[2], ROOF[3], Z_EAVES - 20, MAT["soffit"])
for (a, b_, c, d) in ((ROOF[0], ROOF[1] - 30, ROOF[2], ROOF[1] + 20), (ROOF[0], ROOF[3] - 20, ROOF[2], ROOF[3] + 30),
                      (ROOF[0] - 30, ROOF[1], ROOF[0] + 20, ROOF[3]), (ROOF[2] - 20, ROOF[1], ROOF[2] + 30, ROOF[3])):
    box("Lobovoy", a, b_, Z_EAVES - 220, c, d, Z_EAVES + 20, MAT["fascia"])
# желоба и трубы
for (a, b_, c, d) in ((ROOF[0], ROOF[1] - 150, ROOF[2], ROOF[1] - 30), (ROOF[0], ROOF[3] + 30, ROOF[2], ROOF[3] + 150)):
    box("Tarnov", a, b_, Z_EAVES - 120, c, d, Z_EAVES + 10, MAT["fascia"])
for (px, py) in ((ROOF[0] + 150, ROOF[3] + 90), (ROOF[2] - 150, ROOF[3] + 90), (X0 - 80, -350), (X1 + 80, -350)):
    cyl("Quvur", px * M, py * M, Z_GROUND * M + 0.15, Z_EAVES * M - 0.1, 0.05, MAT["fascia"])

# ---- айван ----
box("Ayvon pol", AYVON[0], AYVON[1], Z_GROUND, AYVON[2], AYVON[3], Z_AYVON, MAT["tile"])
for i, (cx, cy) in enumerate(AYVON_COLS):
    cyl(f"Ustun{i}", cx * M, cy * M, Z_AYVON * M, 2.70, COL_D / 2 * M, MAT["column"])
    box(f"UstunBaza{i}", cx - 180, cy - 180, Z_AYVON, cx + 180, cy + 180, Z_AYVON + 120, MAT["column"])
box("Ayvon balka", AYVON_ROOF[0], -3300, 2700, AYVON_ROOF[2], -3000, 2900, MAT["column"])
ax1, ay1, ax2, ay2 = [v * M for v in AYVON_ROOF]
hi, lo = Z_AYV_HI * M, Z_AYV_LO * M
ob = mesh_from("Ayvon tom", [(ax1, ay2, hi), (ax1, ay1, lo), (ax2, ay1, lo), (ax2, ay2, hi)], [[0, 1, 2, 3]], MAT["roof"], C_HOUSE)
ob.modifiers.new("q", "SOLIDIFY").thickness = 0.04
mesh_from("Ayvon shift", [(ax1, ay2, hi - 0.08), (ax2, ay2, hi - 0.08), (ax2, ay1, lo - 0.08), (ax1, ay1, lo - 0.08)],
          [[0, 1, 2, 3]], MAT["soffit"], C_HOUSE)
box("Ayvon lobovoy", AYVON_ROOF[0], AYVON_ROOF[1] - 30, Z_AYV_LO - 200, AYVON_ROOF[2], AYVON_ROOF[1] + 20, Z_AYV_LO + 30, MAT["fascia"])
for i, x in enumerate(range(1500, 15000, 2600)):
    yy = -1700
    zz = (Z_AYV_HI + (Z_AYV_LO - Z_AYV_HI) * (-yy - 200) / 3500) * M - 0.085
    cyl(f"Spot{i}", x * M, yy * M, zz - 0.01, zz, 0.06, MAT["lamp"], verts=16)
    L = bpy.data.lights.new(f"SpotL{i}", "POINT"); L.energy = 35; L.color = (1.0, 0.78, 0.55); L.shadow_soft_size = 0.05
    lo_ = bpy.data.objects.new(f"SpotL{i}", L); lo_.location = (x * M, yy * M, zz - 0.06); C_HOUSE.objects.link(lo_)
# ступени
for i, (ya, yb, zt) in enumerate(((-3700, -3400, -250), (-4000, -3700, -350))):
    box(f"Zina{i}", 700, ya, Z_GROUND, 2100, yb, zt, MAT["tile"])
# настенные светильники у входа
for x in (600, 2200):
    box("Bra", x - 60, Y0 - 90, 2200, x + 60, Y0 - 20, 2400, MAT["lamp"])

# ---- свет в комнатах (тёплый вечерний) ----
for n, name, code, rs in rooms:
    r = max(rs, key=lambda r: (r[2] - r[0]) * (r[3] - r[1]))
    L = bpy.data.lights.new(f"Xona{n}", "AREA"); L.size = 1.2; L.color = (1.0, 0.72, 0.45)
    L.energy = 180 if code != "Кор" else 90
    o = bpy.data.objects.new(f"Xona{n}", L); o.location = ((r[0] + r[2]) / 2 * M, (r[1] + r[3]) / 2 * M, 2.9)
    C_HOUSE.objects.link(o)

# ---------------- участок ----------------
px1, py1, px2, py2 = PLOT_FACT
box("Atrof yer", -60000, -60000, Z_GROUND - 40, 80000, 80000, Z_GROUND - 20, MAT["dirt"], C_SITE)
box("Hovli qoplama", px1, py1, Z_GROUND - 20, px2, py2, Z_GROUND, MAT["paver"], C_SITE)
box("Otmostka", X0 - 1000, Y0, Z_GROUND, X1 + 1000, Y1 + 1000, Z_GROUND + 30, MAT["concrete"], C_SITE)
box("Yo'lak", 800, py1, Z_GROUND, 2200, -4000, Z_GROUND + 15, MAT["paver"], C_SITE)
box("Bostirma pol", BOSTIRMA[0], py1, Z_GROUND, BOSTIRMA[2], BOSTIRMA[3], Z_GROUND + 30, MAT["concrete"], C_SITE)
# улица
box("Ko'cha", -60000, -21500, Z_GROUND - 20, 80000, -15500, Z_GROUND - 5, MAT["asphalt"], C_SITE)
box("Trotuar", -60000, -15500, Z_GROUND - 20, 80000, -14200, Z_GROUND + 120, MAT["concrete"], C_SITE)
for x in range(-60000, 80000, 6000):
    box("Chiziq", x, -18550, Z_GROUND - 5, x + 3000, -18450, Z_GROUND, MAT["line"], C_SITE)

# газоны
LAWNS = [(-3600, -13600, 700, -4300), (2300, -13600, 12100, -4300), (-3600, 12500, 21600, 25600),
         (-3600, -3200, X0 - 1100, 12400), (X1 + 1100, -3200, 21600, 12400)]
lawn_objs = []
for i, (a, b_, c, d) in enumerate(LAWNS):
    lawn_objs.append(box(f"Gazon{i}", a, b_, Z_GROUND, c, d, Z_GROUND + 20, MAT["soil"], C_VEG))

# ограда
FH = 1900
def fence(a, b_, c, d, gaps=()):
    horiz = c - a > d - b_
    s0, s1 = (a, c) if horiz else (b_, d)
    pos = s0
    for g0, g1 in sorted(gaps) + [(s1, s1)]:
        if g0 > pos:
            if horiz:
                box("Devor_tashqi", pos, b_, Z_GROUND, g0, d, Z_GROUND + FH, MAT["plaster"], C_SITE)
                box("Qopqoq", pos - 20, b_ - 30, Z_GROUND + FH, g0 + 20, d + 30, Z_GROUND + FH + 60, MAT["cap"], C_SITE)
            else:
                box("Devor_tashqi", a, pos, Z_GROUND, c, g0, Z_GROUND + FH, MAT["plaster"], C_SITE)
                box("Qopqoq", a - 30, pos - 20, Z_GROUND + FH, c + 30, g0 + 20, Z_GROUND + FH + 60, MAT["cap"], C_SITE)
        pos = g1
fence(px1, py1 - 200, px2, py1, gaps=[(800, 2200), (12700, 18300)])
fence(px1, py2, px2, py2 + 200)
fence(px1 - 200, py1, px1, py2)
fence(px2, py1, px2 + 200, py2)
box("Darvoza", 12700, py1 - 160, Z_GROUND, 18300, py1 - 40, Z_GROUND + FH - 100, MAT["metal_dark"], C_SITE)
box("Kichik eshik", 800, py1 - 160, Z_GROUND, 2200, py1 - 40, Z_GROUND + FH - 100, MAT["metal_dark"], C_SITE)

# навес (бостирма)
bx, by = BOSTIRMA[0], BOSTIRMA[1]
for cx in (300, 3000, 5700):
    for cy in (300, 5700):
        box("Bostirma ustun", bx + cx - 50, by + cy - 50, Z_GROUND, bx + cx + 50, by + cy + 50, 2550, MAT["metal_dark"], C_SITE)
ob = mesh_from("Bostirma tom", [((bx - 300) * M, (by - 300) * M, 2.55), ((bx + 6300) * M, (by - 300) * M, 2.55),
                                ((bx + 6300) * M, (by + 6300) * M, 2.80), ((bx - 300) * M, (by + 6300) * M, 2.80)],
               [[0, 1, 2, 3]], MAT["roof"], C_SITE)
ob.modifiers.new("q", "SOLIDIFY").thickness = 0.04
box("Bostirma balka", bx - 300, by + 200, 2400, bx + 6300, by + 400, 2560, MAT["metal_dark"], C_SITE)
box("Bostirma balka", bx - 300, by + 5600, 2620, bx + 6300, by + 5800, 2800, MAT["metal_dark"], C_SITE)

# существующая хозпостройка
ox1, oy1, ox2, oy2 = OMBOR
box("Ombor", ox1, oy1, Z_GROUND, ox2, oy2, 2400, MAT["plaster"], C_SITE)
box("Ombor sokol", ox1 - 20, oy1 - 20, Z_GROUND, ox2 + 20, oy2 + 20, -150, MAT["plinth"], C_SITE)
box("Ombor eshik", ox1 + 800, oy1 - 30, Z_GROUND, ox1 + 1700, oy1 + 10, 1700, MAT["door"], C_SITE)
mz = (oy1 + oy2) / 2
for sgn in (-1, 1):
    yy0 = oy1 - 300 if sgn < 0 else oy2 + 300
    mesh_from("Ombor tom", [((ox1 - 300) * M, yy0 * M, 2.35), ((ox2 + 300) * M, yy0 * M, 2.35),
                             ((ox2 + 300) * M, mz * M, 3.2), ((ox1 - 300) * M, mz * M, 3.2)],
              [[0, 1, 2, 3] if sgn < 0 else [1, 0, 3, 2]], MAT["roof"], C_SITE).modifiers.new("q", "SOLIDIFY").thickness = 0.04

# соседние дома (контекст)
def simple_house(x, y, w, d, h=3200, name="Qo'shni"):
    box(name, x, y, Z_GROUND, x + w, y + d, h, MAT["plaster"], C_CTX)
    box(name + " sokol", x - 20, y - 20, Z_GROUND, x + w + 20, y + d + 20, 0, MAT["plinth"], C_CTX)
    o = 500; X_, Y_ = (x - o) * M, (y - o) * M; W_, D_ = (w + 2 * o) * M, (d + 2 * o) * M
    hz = h * M; r = min(W_, D_) / 2; rz_ = hz + r * 0.4
    if W_ >= D_:
        vs = [(X_, Y_, hz), (X_ + W_, Y_, hz), (X_ + W_, Y_ + D_, hz), (X_, Y_ + D_, hz), (X_ + r, Y_ + r, rz_), (X_ + W_ - r, Y_ + r, rz_)]
        fs_ = [[0, 1, 5, 4], [2, 3, 4, 5], [3, 0, 4], [1, 2, 5]]
    else:
        vs = [(X_, Y_, hz), (X_ + W_, Y_, hz), (X_ + W_, Y_ + D_, hz), (X_, Y_ + D_, hz), (X_ + r, Y_ + r, rz_), (X_ + r, Y_ + D_ - r, rz_)]
        fs_ = [[0, 1, 4], [1, 2, 5, 4], [2, 3, 5], [3, 0, 4, 5]]
    mesh_from(name + " tom", vs, fs_, MAT["roof"], C_CTX).modifiers.new("q", "SOLIDIFY").thickness = 0.04
simple_house(-20000, -4000, 13000, 10000)
simple_house(27000, -2000, 11000, 12000)
simple_house(-12000, -42000, 14000, 11000)
simple_house(8000, -40000, 12000, 10000)
simple_house(26000, -41000, 12000, 11000)
simple_house(-18000, 16000, 10000, 9000)
simple_house(28000, 17000, 10000, 9000)
for (a, b_, c, d) in ((-22000, -14200, -4200, -14000), (22200, -14200, 40000, -14000), (-22000, -22000, 40000, -21800)):
    box("Qo'shni devor", a, b_, Z_GROUND, c, d, Z_GROUND + 1800, MAT["plaster"], C_CTX)

# ---------------- растительность (Geometry Nodes, экземпляры) ----------------
def src_obj(name, verts, faces, mat):
    o = mesh_from(name, verts, faces, mat, C_SRC)
    return o

# пучок травы: 9 травинок
gv, gf = [], []
for i in range(9):
    a = random.uniform(0, 2 * math.pi); r = random.uniform(0, 0.035)
    cx, cy = r * math.cos(a), r * math.sin(a)
    h = random.uniform(0.06, 0.13); w = 0.004
    lean = random.uniform(0, 2 * math.pi); ld = random.uniform(0.01, 0.04)
    dx, dy = math.cos(a + 1.57) * w, math.sin(a + 1.57) * w
    tx, ty = cx + math.cos(lean) * ld, cy + math.sin(lean) * ld
    base = len(gv)
    gv += [(cx - dx, cy - dy, 0), (cx + dx, cy + dy, 0), (cx + (tx - cx) * 0.6 + dx * 0.6, cy + (ty - cy) * 0.6 + dy * 0.6, h * 0.6),
           (cx + (tx - cx) * 0.6 - dx * 0.6, cy + (ty - cy) * 0.6 - dy * 0.6, h * 0.6), (tx, ty, h)]
    gf += [[base, base + 1, base + 2, base + 3], [base + 3, base + 2, base + 4]]
GRASS = src_obj("_otbosh", gv, gf, MAT["grass"])
LEAF = src_obj("_barg", [(0, -0.02, 0), (0.05, -0.022, 0.003), (0.1, 0, 0.006), (0.05, 0.022, 0.003), (0, 0.02, 0)],
               [[0, 1, 2, 3, 4]], MAT["leaf"])
LEAF_B = src_obj("_barg_buxus", [(0, -0.012, 0), (0.03, -0.013, 0), (0.05, 0, 0), (0.03, 0.013, 0), (0, 0.012, 0)], [[0, 1, 2, 3, 4]], MAT["boxwood"])
LAV = src_obj("_lavanda", [(0, -0.006, 0), (0.006, 0, 0.0), (0, 0.006, 0), (0, 0, 0.12)], [[0, 1, 3], [1, 2, 3], [2, 0, 3]], MAT["lavender"])
for o in (GRASS, LEAF, LEAF_B, LAV):
    o.hide_render = True; o.hide_viewport = True

def _sock(socks, name, typ):
    for x in socks:
        if x.name == name and x.type == typ:
            return x
    raise KeyError(name + "/" + typ)

def scatter(obj, inst, density, rmin, rmax, smin, smax, seed=0, keep=True):
    ng = bpy.data.node_groups.new(f"SC_{obj.name}", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    N, Lk = ng.nodes, ng.links
    gi, go = N.new("NodeGroupInput"), N.new("NodeGroupOutput")
    ds = N.new("GeometryNodeDistributePointsOnFaces")
    ds.inputs["Density"].default_value = density; ds.inputs["Seed"].default_value = seed
    oi = N.new("GeometryNodeObjectInfo"); oi.inputs["Object"].default_value = inst
    io = N.new("GeometryNodeInstanceOnPoints")
    rv = N.new("FunctionNodeRandomValue"); rv.data_type = "FLOAT_VECTOR"
    _sock(rv.inputs,"Min","VECTOR").default_value = rmin; _sock(rv.inputs,"Max","VECTOR").default_value = rmax; rv.inputs["Seed"].default_value = seed + 1
    rs = N.new("FunctionNodeRandomValue"); rs.data_type = "FLOAT"
    _sock(rs.inputs,"Min","VALUE").default_value = smin; _sock(rs.inputs,"Max","VALUE").default_value = smax; rs.inputs["Seed"].default_value = seed + 2
    Lk.new(gi.outputs[0], ds.inputs["Mesh"]); Lk.new(ds.outputs["Points"], io.inputs["Points"])
    Lk.new(oi.outputs["Geometry"], io.inputs["Instance"])
    Lk.new(_sock(rv.outputs,"Value","VECTOR"), io.inputs["Rotation"]); Lk.new(_sock(rs.outputs,"Value","VALUE"), io.inputs["Scale"])
    if keep:
        j = N.new("GeometryNodeJoinGeometry")
        Lk.new(gi.outputs[0], j.inputs[0]); Lk.new(io.outputs[0], j.inputs[0]); Lk.new(j.outputs[0], go.inputs[0])
    else:
        Lk.new(io.outputs[0], go.inputs[0])
    obj.modifiers.new("tarqatish", "NODES").node_group = ng

dens = 70 if MODE == "test" else 260
for i, o in enumerate(lawn_objs):
    scatter(o, GRASS, dens, (0, 0, 0), (0.25, 0.25, 6.283), 0.7, 1.4, seed=i * 7)

def blob(name, x, y, z, rx, ry, rz, subd=3):
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=subd, radius=1.0)
    for v in bm.verts:
        n = random.uniform(0.85, 1.12)
        v.co = Vector((v.co.x * rx * n, v.co.y * ry * n, v.co.z * rz * n))
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); o.location = (x, y, z); C_VEG.objects.link(o)
    return o

def tree(x, y, h=4.0, r=1.7, seed=0):
    x, y = x * M, y * M
    zg = Z_GROUND * M
    trunk_h = h * 0.45
    t = cyl("Tana", x, y, zg, zg + trunk_h + r * 0.5, 0.09 * h / 4, MAT["bark"], C_VEG, 10)
    for k_ in range(random.randint(2, 4)):
        a = random.uniform(0, 6.28); rr_ = r * random.uniform(0.45, 0.7)
        cz = zg + trunk_h + r * random.uniform(0.6, 1.1)
        c = blob("Toj", x + math.cos(a) * rr_ * 0.6, y + math.sin(a) * rr_ * 0.6, cz, rr_ * 1.1, rr_ * 1.1, rr_ * 0.9)
        c.data.materials.append(MAT["leaf_inner"])
        c2 = blob("Barglar", c.location.x, c.location.y, c.location.z, rr_ * 1.18, rr_ * 1.18, rr_ * 0.98)
        scatter(c2, LEAF, 550 if MODE != "test" else 200, (0, 0, 0), (6.28, 6.28, 6.28), 0.8, 1.4, seed=seed + k_, keep=False)
    c = blob("Toj", x, y, zg + trunk_h + r, r, r, r * 0.85)
    c.data.materials.append(MAT["leaf_inner"])
    c2 = blob("Barglar", x, y, zg + trunk_h + r, r * 1.08, r * 1.08, r * 0.92)
    scatter(c2, LEAF, 550 if MODE != "test" else 200, (0, 0, 0), (6.28, 6.28, 6.28), 0.8, 1.4, seed=seed + 11, keep=False)

def shrub(x, y, r=0.45, kind="buxus", seed=0):
    zg = Z_GROUND * M
    c = blob("Buta", x * M, y * M, zg + r * 0.75, r * 0.92, r * 0.92, r * 0.72, 2)
    c.data.materials.append(MAT["leaf_inner"])
    c2 = blob("Buta barg", x * M, y * M, zg + r * 0.75, r, r, r * 0.8, 3)
    if kind == "lavanda":
        scatter(c2, LAV, 900 if MODE != "test" else 300, (-0.3, -0.3, 0), (0.3, 0.3, 6.28), 0.7, 1.3, seed=seed, keep=False)
    else:
        scatter(c2, LEAF_B, 1800 if MODE != "test" else 500, (0, 0, 0), (6.28, 6.28, 6.28), 0.8, 1.3, seed=seed, keep=False)

# деревья во дворе и за оградой
for i, (tx, ty, h, r) in enumerate([(-1500, 15500, 4.2, 1.7), (3500, 17500, 4.6, 1.9), (8500, 15500, 4.0, 1.6),
                                    (2000, 22500, 4.8, 2.0), (8000, 22500, 4.4, 1.8), (19500, 16000, 4.0, 1.6),
                                    (-2000, -11500, 4.4, 1.8), (9500, -11000, 3.8, 1.5), (5500, -12000, 4.0, 1.6),
                                    (-1800, 9000, 3.6, 1.4), (19800, 9500, 3.8, 1.5)]):
    tree(tx, ty, h, r, seed=i * 13)
for i, (tx, ty) in enumerate([(-9000, -10000), (-6500, 5000), (25000, -8000), (30000, 13000), (-9000, 20000), (4000, 30000),
                              (16000, 31000), (-4000, -26000), (20000, -26000), (40000, 0)]):
    tree(tx, ty, random.uniform(4.5, 6.5), random.uniform(2.0, 2.6), seed=200 + i)
# кусты вдоль айвана: лаванда и самшит
for i, x in enumerate(range(3000, 12000, 1100)):
    shrub(x, -4900, 0.35 if i % 2 else 0.42, "lavanda" if i % 2 == 0 else "buxus", seed=300 + i)
for i, y in enumerate(range(-2500, 11000, 1600)):
    shrub(X1 + 1700, y, 0.45, "buxus", seed=400 + i)

# ---------------- небо, солнце ----------------
world = bpy.data.worlds.new("Osmon"); sc.world = world
try:
    world.use_nodes = True
except Exception:
    pass
wn = world.node_tree
bg = next(n for n in wn.nodes if n.type == "BACKGROUND")
sky = wn.nodes.new("ShaderNodeTexSky")
types = [i.identifier for i in bpy.types.ShaderNodeTexSky.bl_rna.properties["sky_type"].enum_items]
for t in ("MULTIPLE_SCATTERING", "NISHITA", "SINGLE_SCATTERING"):
    if t in types:
        sky.sky_type = t; break
SUN_EL, SUN_AZ = math.radians(11), math.radians(205)   # азимут от +Y по часовой: солнце на юго-западе
for attr, val in (("sun_elevation", SUN_EL), ("sun_rotation", SUN_AZ), ("sun_disc", False), ("altitude", 400.0),
                  ("air_density", 1.2), ("dust_density", 2.5)):
    try:
        setattr(sky, attr, val)
    except Exception:
        pass
wn.links.new(sky.outputs[0], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 0.35
sun_dir = Vector((math.sin(SUN_AZ) * math.cos(SUN_EL), math.cos(SUN_AZ) * math.cos(SUN_EL), math.sin(SUN_EL)))
L = bpy.data.lights.new("Quyosh", "SUN"); L.energy = 3.2; L.color = (1.0, 0.70, 0.45); L.angle = math.radians(1.2)
so = bpy.data.objects.new("Quyosh", L); sc.collection.objects.link(so)
so.rotation_euler = sun_dir.to_track_quat("Z", "Y").to_euler()

# ---------------- камеры ----------------
def camera(name, loc, target, lens=24):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.clip_end = 400
    co = bpy.data.objects.new(name, cd); co.location = loc; sc.collection.objects.link(co)
    co.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return co
CAMS = {
    "front": camera("Kamera_old", (-2.8, -12.6, 1.65), (8.5, -0.5, 1.6), 22),
    "ayvon": camera("Kamera_ayvon", (14.2, -7.6, 1.6), (4.0, -1.2, 1.5), 20),
    "back": camera("Kamera_orqa", (-2.6, 23.8, 1.7), (10.0, 9.0, 1.9), 22),
    "side": camera("Kamera_yon", (21.0, -10.5, 1.7), (7.0, 3.0, 1.7), 22),
    "aerial": camera("Kamera_tepa", (-16.0, -30.0, 21.0), (9.0, 6.0, -1.0), 28),
}

# ---------------- рендер ----------------
try:
    sc.render.engine = "CYCLES"
except TypeError as e:
    print("engine:", e)
cy = sc.cycles
cy.device = "CPU"
cy.samples = 24 if MODE == "test" else 160
cy.use_denoising = True
try:
    cy.denoiser = "OPENIMAGEDENOISE"
except Exception:
    pass
cy.max_bounces = 6; cy.caustics_reflective = False; cy.caustics_refractive = False
cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.02
sc.render.resolution_x, sc.render.resolution_y = (800, 500) if MODE == "test" else (1920, 1200)
sc.render.resolution_percentage = 100
vts = [i.identifier for i in bpy.types.ColorManagedViewSettings.bl_rna.properties["view_transform"].enum_items]
sc.view_settings.view_transform = "AgX"
try:
    looks = [i.identifier for i in bpy.types.ColorManagedViewSettings.bl_rna.properties["look"].enum_items]
    for lk in looks:
        if "Medium High Contrast" in lk:
            sc.view_settings.look = lk; break
except Exception:
    pass
sc.view_settings.exposure = 0.3
sc.render.image_settings.file_format = "PNG"

os.makedirs(os.path.join(OUT, "3D"), exist_ok=True)
rdir = os.path.join(OUT, "RENDER" if MODE == "final" else "_render_test")
os.makedirs(rdir, exist_ok=True)
if MODE == "final" or "save" in VIEWS:
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "3D", "NAMUNA 7-UY.blend"), compress=True)
for vname in VIEWS:
    if vname not in CAMS:
        continue
    sc.camera = CAMS[vname]
    sc.render.filepath = os.path.join(rdir, f"{vname}.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", vname, flush=True)
print("DONE")
