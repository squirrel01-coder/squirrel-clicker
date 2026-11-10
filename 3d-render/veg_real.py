"""Живая растительность и детали для realism.py: газон пучками, лаванда стеблями с колосками,
самшит мелким листом по нормали, потемнения на штукатурке, окна у соседних домов, деревья вдоль улицы."""
import bpy, bmesh, math, random
from mathutils import Vector

def _mesh(name, verts, faces, mats, mat_idx=None):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    for m in mats: me.materials.append(m)
    if mat_idx:
        for p, i in zip(me.polygons, mat_idx): p.material_index = i
    return me

def grass_clump(rng):
    V, F = [], []
    for _ in range(28):
        a = rng.uniform(0, 6.283); r0 = rng.uniform(0, 0.03)
        bx, by = r0 * math.cos(a), r0 * math.sin(a)
        h = rng.uniform(0.04, 0.09); w = rng.uniform(0.0018, 0.003)
        lean = rng.uniform(0.1, 0.35) * h; la = a + rng.uniform(-0.6, 0.6)
        px, py = -math.sin(la) * w, math.cos(la) * w
        seg = 4; base = len(V)
        for k in range(seg + 1):
            t = k / seg; ww = (1 - t) ** 0.8
            cx = bx + math.cos(la) * lean * t * t; cy = by + math.sin(la) * lean * t * t; cz = h * t * (1 - 0.15 * t)
            if k < seg:
                V += [(cx - px * ww, cy - py * ww, cz), (cx + px * ww, cy + py * ww, cz)]
            else:
                V += [(cx, cy, cz)]
        for k in range(seg - 1):
            i = base + 2 * k; F.append([i, i + 1, i + 3, i + 2])
        i = base + 2 * (seg - 1); F.append([i, i + 1, i + 2])
    return V, F

def lavender_stem(rng):
    V, F, idx = [], [], []
    def prism(x0, y0, z0, z1, r, mi):
        b = len(V)
        for z in (z0, z1):
            for k in range(4):
                a = k * 1.5708; V.append((x0 + r * math.cos(a), y0 + r * math.sin(a), z))
        for k in range(4):
            F.append([b + k, b + (k + 1) % 4, b + 4 + (k + 1) % 4, b + 4 + k]); idx.append(mi)
    L = rng.uniform(0.16, 0.26)
    prism(0, 0, 0, L, 0.0012, 0)
    n = 9
    for k in range(n):                     # колосок: мутовки цветков, к верху мельче
        z = L + k * 0.007; r = 0.0045 * (1 - 0.5 * k / n)
        prism(0, 0, z, z + 0.006, r, 1)
    return V, F, idx

def boxwood_leaf():
    V = [(0, -0.006, 0.0), (0.008, -0.007, 0.001), (0.016, 0, 0.002), (0.008, 0.007, 0.001), (0, 0.006, 0.0), (0.008, 0, -0.0008)]
    F = [[0, 1, 5], [1, 2, 5], [2, 3, 5], [3, 4, 5], [4, 0, 5]]
    return V, F

def principled(name, color, rough, sss=0.0, sheen=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*color, 1); b.inputs["Roughness"].default_value = rough
    return m, b

def random_tint(m, b, c1, c2, coord_z_dark=None):
    """Оттенок у каждого экземпляра свой; для травы — темнее у основания."""
    nt = m.node_tree
    oi = nt.nodes.new("ShaderNodeObjectInfo")
    ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.elements[0].color = (*c1, 1); ramp.color_ramp.elements[1].color = (*c2, 1)
    nt.links.new(oi.outputs["Random"], ramp.inputs["Fac"])
    col = ramp.outputs["Color"]
    if coord_z_dark:
        tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Object"], sep.inputs[0])
        mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 0; mr.inputs["From Max"].default_value = coord_z_dark
        mr.inputs["To Min"].default_value = 0.6; mr.inputs["To Max"].default_value = 1.0
        nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
        mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs[0].default_value = 1
        nt.links.new(col, mx.inputs[6]); nt.links.new(mr.outputs["Result"], mx.inputs[7]); col = mx.outputs[2]
        # кончики светлее и желтее
        mr2 = nt.nodes.new("ShaderNodeMapRange"); mr2.inputs["From Min"].default_value = coord_z_dark * 0.7; mr2.inputs["From Max"].default_value = coord_z_dark * 1.4
        nt.links.new(sep.outputs["Z"], mr2.inputs["Value"])
        mx2 = nt.nodes.new("ShaderNodeMix"); mx2.data_type = "RGBA"; mx2.inputs[7].default_value = (0.20, 0.28, 0.07, 1)
        nt.links.new(mr2.outputs["Result"], mx2.inputs[0]); nt.links.new(col, mx2.inputs[6]); col = mx2.outputs[2]
    nt.links.new(col, b.inputs["Base Color"])
    # просвечивание
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    tr = nt.nodes.new("ShaderNodeBsdfTranslucent"); nt.links.new(col, tr.inputs["Color"])
    mix = nt.nodes.new("ShaderNodeMixShader"); mix.inputs[0].default_value = 0.25
    nt.links.new(b.outputs[0], mix.inputs[1]); nt.links.new(tr.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs["Surface"])

def set_scatter(obj_prefix, density, align_normal, smin=None, smax=None):
    for o in bpy.data.objects:
        if not o.name.startswith(obj_prefix): continue
        for md in o.modifiers:
            if md.type != "NODES": continue
            ng = md.node_group
            ds = next(n for n in ng.nodes if n.type == "DISTRIBUTE_POINTS_ON_FACES")
            ds.inputs["Density"].default_value = density
            io = next(n for n in ng.nodes if n.type == "INSTANCE_ON_POINTS")
            if align_normal:
                # поворот по нормали поверхности + случайный поворот вокруг неё
                rot = next(s for s in ds.outputs if s.name == "Rotation")
                rr = ng.nodes.new("FunctionNodeRotateRotation"); rr.rotation_space = "LOCAL"
                rv = ng.nodes.new("FunctionNodeRandomValue"); rv.data_type = "FLOAT_VECTOR"
                mn = next(s for s in rv.inputs if s.name == "Min" and s.type == "VECTOR"); mx = next(s for s in rv.inputs if s.name == "Max" and s.type == "VECTOR")
                mn.default_value = (-0.35, -0.35, 0); mx.default_value = (0.35, 0.35, 6.283)
                er = ng.nodes.new("FunctionNodeEulerToRotation")
                ng.links.new(next(s for s in rv.outputs if s.type == "VECTOR"), er.inputs[0])
                ng.links.new(rot, rr.inputs[0]); ng.links.new(er.outputs[0], rr.inputs[1])
                ng.links.new(rr.outputs[0], io.inputs["Rotation"])
            if smin is not None:
                rs = [n for n in ng.nodes if n.type == "RANDOM_VALUE" and n.data_type == "FLOAT"]
                for n in rs:
                    next(s for s in n.inputs if s.name == "Min" and s.type == "VALUE").default_value = smin
                    next(s for s in n.inputs if s.name == "Max" and s.type == "VALUE").default_value = smax

PBR = None
def apply(M_, geom, quality_final):
    rng = random.Random(11)
    # --- газон
    g, gb = principled("O't jonli", (0.1, 0.2, 0.04), 0.45)
    random_tint(g, gb, (0.05, 0.13, 0.018), (0.13, 0.23, 0.04), coord_z_dark=0.07)
    V, F = grass_clump(rng); src = bpy.data.objects["_otbosh"]; src.data = _mesh("otbosh_jonli", V, F, [g])
    set_scatter("Gazon", 300 if quality_final else 110, False, 0.7, 1.3)
    soil = bpy.data.materials.get("Tuproq")
    if soil and PBR:
        PBR(soil, "leafy_grass", 1.5, tint=(0.55, 0.85, 0.40), sat=1.1, bump=1.0)   # под травинками — фото настоящего газона
    # --- лаванда
    stem, sb = principled("Lavanda poya", (0.22, 0.27, 0.18), 0.7); random_tint(stem, sb, (0.16, 0.22, 0.12), (0.26, 0.30, 0.20))
    flw, fb = principled("Lavanda gul", (0.25, 0.15, 0.5), 0.6); random_tint(flw, fb, (0.17, 0.09, 0.40), (0.33, 0.20, 0.62))
    V, F, idx = lavender_stem(rng); bpy.data.objects["_lavanda"].data = _mesh("lavanda_jonli", V, F, [stem, flw], idx)
    # --- самшит
    lf, lb = principled("Buxus barg", (0.04, 0.12, 0.02), 0.32); random_tint(lf, lb, (0.02, 0.07, 0.01), (0.07, 0.17, 0.03))
    V, F = boxwood_leaf(); bpy.data.objects["_barg_buxus"].data = _mesh("buxus_jonli", V, F, [lf])
    for o in bpy.data.objects:
        if not o.name.startswith("Buta barg"): continue
        md = next((m for m in o.modifiers if m.type == "NODES"), None)
        if not md: continue
        inst = next(n for n in md.node_group.nodes if n.type == "OBJECT_INFO").inputs["Object"].default_value
        if inst and inst.name == "_lavanda":
            set_scatter(o.name, 1400 if quality_final else 500, True, 0.8, 1.2)
        else:
            set_scatter(o.name, 9000 if quality_final else 3000, True, 0.8, 1.3)
    # внутренний «шар» куста — тёмный, чтобы не просвечивал
    # --- штукатурка: потемнение у земли и лёгкие разводы
    pl = bpy.data.materials["Suvoq"]; nt = pl.node_tree; b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    src_col = b.inputs["Base Color"].links[0].from_socket
    tc = nt.nodes.new("ShaderNodeTexCoord"); sep = nt.nodes.new("ShaderNodeSeparateXYZ"); nt.links.new(tc.outputs["Object"], sep.inputs[0])
    mr = nt.nodes.new("ShaderNodeMapRange"); mr.inputs["From Min"].default_value = 0.0; mr.inputs["From Max"].default_value = 0.9
    mr.inputs["To Min"].default_value = 0.80; mr.inputs["To Max"].default_value = 1.0; nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    nz = nt.nodes.new("ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 1.3; nz.inputs["Detail"].default_value = 6
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    nr = nt.nodes.new("ShaderNodeMapRange"); nr.inputs["To Min"].default_value = 0.93; nr.inputs["To Max"].default_value = 1.03
    nt.links.new(nz.outputs["Fac"], nr.inputs["Value"])
    m1 = nt.nodes.new("ShaderNodeMath"); m1.operation = "MULTIPLY"; nt.links.new(mr.outputs["Result"], m1.inputs[0]); nt.links.new(nr.outputs["Result"], m1.inputs[1])
    mx = nt.nodes.new("ShaderNodeMix"); mx.data_type = "RGBA"; mx.blend_type = "MULTIPLY"; mx.inputs[0].default_value = 1
    nt.links.new(src_col, mx.inputs[6]); nt.links.new(m1.outputs[0], mx.inputs[7]); nt.links.new(mx.outputs[2], b.inputs["Base Color"])

def neighbors(M_):
    """Окна и двери у соседних домов (раньше были глухие коробки)."""
    col = bpy.data.collections["Atrof"]
    gl, gb = principled("Qo'shni oyna", (0.02, 0.025, 0.03), 0.05); gb.inputs["Metallic"].default_value = 0.0
    gb.inputs["Specular IOR Level"].default_value = 1.0; gb.inputs["Coat Weight"].default_value = 1.0
    warm, wb = principled("Qo'shni nur", (0.9, 0.7, 0.45), 0.5); wb.inputs["Emission Color"].default_value = (1, 0.66, 0.36, 1); wb.inputs["Emission Strength"].default_value = 4
    fr = bpy.data.materials["PVX rom"]
    rng = random.Random(5)
    for o in list(col.objects):
        if o.name.split(".")[0] != "Qo'shni" or o.type != "MESH": continue
        xs = [v.co.x for v in o.data.vertices]; ys = [v.co.y for v in o.data.vertices]; zs = [v.co.z for v in o.data.vertices]
        x0, x1, y0, y1, ztop = min(xs), max(xs), min(ys), max(ys), max(zs)
        for side in ("S", "N", "W", "E"):
            L = (x1 - x0) if side in "SN" else (y1 - y0)
            n = int(L // 3.2)
            for k in range(n):
                u = (k + 0.5) * L / n - 0.75
                lit = rng.random() < 0.35
                for (d0, d1, a0, a1, z0, z1, m) in ((-0.04, 0.0, u - 0.06, u + 1.56, 0.84, 2.26, fr), (-0.02, 0.01, u, u + 1.5, 0.9, 2.2, warm if lit else gl)):
                    if side == "S": p0, p1 = (x0 + a0, y0 + d0, z0), (x0 + a1, y0 + d1, z1)
                    elif side == "N": p0, p1 = (x0 + a0, y1 - d1, z0), (x0 + a1, y1 - d0, z1)
                    elif side == "W": p0, p1 = (x0 + d0, y0 + a0, z0), (x0 + d1, y0 + a1, z1)
                    else: p0, p1 = (x1 - d1, y0 + a0, z0), (x1 - d0, y0 + a1, z1)
                    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
                    me = bpy.data.meshes.new("QO"); bm.to_mesh(me); bm.free(); me.materials.append(m)
                    ob = bpy.data.objects.new("Qo'shni oyna", me); col.objects.link(ob)
                    ob.location = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2, (p0[2] + p1[2]) / 2)
                    ob.scale = (abs(p1[0] - p0[0]) or 0.01, abs(p1[1] - p0[1]) or 0.01, p1[2] - p0[2])
