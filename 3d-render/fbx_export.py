"""Выгрузка фотореалистичной сцены в FBX для 3ds Max (вызывается из realism.py при EXPORT_FBX=<папка>).
- фото-текстуры с «запечённым» оттенком, нормали, шероховатость; UV «кубом» в реальном масштабе текстуры;
- рассеивание (лаванда, самшит) превращено в настоящую геометрию; трава газона — текстурой;
- деревья на участке — настоящими объектами; деревья за участком (фон для вида сверху) не выгружаются;
- детали одного вида объединены, всё по группам; камеры 6 ракурсов."""
import bpy, bmesh, os, re, math
import numpy as np
from collections import defaultdict
from mathutils import Vector
from PIL import Image

def run(out, TEXSIZE, TEX, CAMS):
    os.makedirs(out, exist_ok=True); tdir = os.path.join(out, "textures"); os.makedirs(tdir, exist_ok=True)
    from geom import PLOT_FACT
    M = 0.001; px1, py1, px2, py2 = [v * M for v in PLOT_FACT]

    # ---- материалы для FBX: картинки напрямую в Base Color / Normal / Roughness
    def bake_diffuse(tex, tint, sat, val):
        d = os.path.join(TEX, tex); f = next(x for x in os.listdir(d) if x.startswith("diff."))
        dst = os.path.join(tdir, f"{tex}_{abs(hash((tint, sat, val))) % 10000}.jpg")
        if not os.path.exists(dst):
            a = np.asarray(Image.open(os.path.join(d, f)).convert("RGB")).astype(np.float32) / 255
            a = a ** 2.2                                                     # в линейное
            g = (a @ np.array([0.2126, 0.7152, 0.0722], np.float32))[..., None]
            a = (g + (a - g) * sat) * val * np.array(tint, np.float32)
            Image.fromarray((np.clip(a, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)).resize((1024, 1024)).save(dst, quality=90)
        return dst
    def copy_map(tex, key):
        d = os.path.join(TEX, tex); f = next((x for x in os.listdir(d) if x.startswith(key + ".")), None)
        if not f: return None
        dst = os.path.join(tdir, f"{tex}_{key}.jpg")
        if not os.path.exists(dst): Image.open(os.path.join(d, f)).convert("RGB").resize((1024, 1024)).save(dst, quality=90)
        return dst
    def simple_mat(m, diff, nor, rough, metal=0.0, rough_val=None):
        nt = m.node_tree
        for n in list(nt.nodes):
            if n.type not in ("OUTPUT_MATERIAL", "BSDF_PRINCIPLED"): nt.nodes.remove(n)
        b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
        out_ = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"); nt.links.new(b.outputs[0], out_.inputs["Surface"])
        t = nt.nodes.new("ShaderNodeTexImage"); t.image = bpy.data.images.load(diff); nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
        if nor:
            tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = bpy.data.images.load(nor); tn.image.colorspace_settings.name = "Non-Color"
            nm = nt.nodes.new("ShaderNodeNormalMap"); nt.links.new(tn.outputs["Color"], nm.inputs["Color"]); nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
        if rough:
            tr = nt.nodes.new("ShaderNodeTexImage"); tr.image = bpy.data.images.load(rough); tr.image.colorspace_settings.name = "Non-Color"
            nt.links.new(tr.outputs["Color"], b.inputs["Roughness"])
        elif rough_val is not None:
            b.inputs["Roughness"].default_value = rough_val
        b.inputs["Metallic"].default_value = metal
    UVSIZE = {}
    for name, (tex, size, tint, sat, val, rot) in TEXSIZE.items():
        m = bpy.data.materials.get(name)
        if not m: continue
        simple_mat(m, bake_diffuse(tex, tint, sat, val), copy_map(tex, "nor"), copy_map(tex, "rough"))
        UVSIZE[name] = (size, rot)
    for name, rot in (("Profnastil", 0), ("Profnastil Y", 90)):
        m = bpy.data.materials.get(name)
        if m:
            simple_mat(m, bake_diffuse("corrugated_iron_02", (0.42, 0.47, 0.56), 0.2, 1.0), copy_map("corrugated_iron_02", "nor"), None, metal=0.55, rough_val=0.38)
            UVSIZE[name] = (1.2, rot)
    for name in ("O't", "Tuproq"):
        m = bpy.data.materials.get(name)
        if m:
            simple_mat(m, bake_diffuse("leafy_grass", (0.8, 1.0, 0.7), 1.1, 1.0), copy_map("leafy_grass", "nor"), copy_map("leafy_grass", "rough"))
            UVSIZE[name] = (2.0, 0)

    # ---- газон: убрать траву-рассеивание (покрытие — текстурой); кусты: рассеивание -> геометрия
    for o in list(bpy.data.objects):
        mods = [m for m in o.modifiers if m.type == "NODES"]
        if not mods: continue
        if o.name.startswith("Gazon"):
            for m in mods: o.modifiers.remove(m)
            if o.data.materials: o.data.materials[0] = bpy.data.materials["Tuproq"]
            continue
        for m in mods:
            ng = m.node_group; go = next(n for n in ng.nodes if n.type == "GROUP_OUTPUT")
            src = go.inputs[0].links[0].from_socket
            ri = ng.nodes.new("GeometryNodeRealizeInstances"); ng.links.new(src, ri.inputs[0]); ng.links.new(ri.outputs[0], go.inputs[0])
    dg = bpy.context.evaluated_depsgraph_get()
    for o in list(bpy.data.objects):
        if o.type == "MESH" and o.modifiers:
            me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
            o.modifiers.clear(); o.data = me

    # ---- деревья участка: экземпляры -> настоящие объекты
    trees_col = bpy.data.collections.new("Daraxtlar"); bpy.context.scene.collection.children.link(trees_col)
    for e in [o for o in bpy.data.objects if o.instance_type == "COLLECTION" and o.instance_collection]:
        x, y = e.location.x, e.location.y
        if px1 <= x <= px2 and py1 <= y <= py2:
            for so in e.instance_collection.objects:
                if so.type != "MESH": continue
                c = so.copy(); c.data = so.data; c.parent = None
                c.matrix_world = e.matrix_world @ so.matrix_world; trees_col.objects.link(c)
        bpy.data.objects.remove(e, do_unlink=True)

    # ---- UV «кубом» в масштабе текстуры, объединение по видам, группы
    def box_uv(me, mw, size, rot):
        bm = bmesh.new(); bm.from_mesh(me); uv = bm.loops.layers.uv.verify()
        c_, s_ = math.cos(math.radians(rot)), math.sin(math.radians(rot))
        for f in bm.faces:
            n = f.normal; ax = max(range(3), key=lambda i: abs(n[i]))
            for l in f.loops:
                p = l.vert.co
                u, v = (p.y, p.z) if ax == 0 else (p.x, p.z) if ax == 1 else (p.x, p.y)
                u, v = (u * c_ - v * s_) / size, (u * s_ + v * c_) / size
                l[uv].uv = (u, v)
        bm.to_mesh(me); bm.free()
    def category(name):
        m_ = re.match(r"[A-Za-z' ]+", name); return (m_.group(0).strip() if m_ else name) or name
    GROUPS = {"Uy": "UY (dom)", "Hovli": "HOVLI (uchastka)", "O'simliklar": "O'SIMLIKLAR (ozelenenie)",
              "Daraxtlar": "DARAXTLAR (derevya)", "Atrof": "ATROF (sosednie doma)"}
    keep = set()
    for cname, gname in GROUPS.items():
        col = bpy.data.collections.get(cname)
        if not col: continue
        parent = bpy.data.objects.new(gname, None); bpy.context.scene.collection.objects.link(parent); keep.add(parent)
        buckets = defaultdict(list)
        for o in col.objects:
            if o.type == "MESH" and not o.hide_render:
                buckets["Daraxt" if cname == "Daraxtlar" else category(o.name)].append(o)
        for cat, objs in buckets.items():
            me = bpy.data.meshes.new(cat); bm = bmesh.new(); mats = []
            for o in objs:
                tmp = o.data.copy(); tmp.transform(o.matrix_world)
                mname = o.material_slots[0].material.name if o.material_slots and o.material_slots[0].material else ""
                if cname != "Daraxtlar" and mname in UVSIZE:
                    box_uv(tmp, None, *UVSIZE[mname])
                idx = []
                for sl in o.material_slots:
                    if sl.material not in mats: mats.append(sl.material)
                    idx.append(mats.index(sl.material))
                tb = bmesh.new(); tb.from_mesh(tmp)
                for f in tb.faces:
                    if idx: f.material_index = idx[min(f.material_index, len(idx) - 1)]
                tb.to_mesh(tmp); tb.free(); bm.from_mesh(tmp); bpy.data.meshes.remove(tmp)
            bm.to_mesh(me); bm.free()
            for m_ in mats: me.materials.append(m_)
            no = bpy.data.objects.new(cat, me); bpy.context.scene.collection.objects.link(no); no.parent = parent; keep.add(no)
            print("FBXOBJ", gname, cat, len(objs), len(me.polygons), flush=True)
    for c in CAMS.values(): keep.add(c)
    for o in list(bpy.data.objects):
        if o not in keep: bpy.data.objects.remove(o, do_unlink=True)
    path = os.path.join(out, "model.fbx")
    bpy.ops.export_scene.fbx(filepath=path, object_types={"EMPTY", "MESH", "CAMERA"}, apply_scale_options="FBX_SCALE_UNITS",
                             mesh_smooth_type="FACE", path_mode="COPY", embed_textures=True)
    print("FBX", path, os.path.getsize(path) // 1024, "KB", flush=True)
