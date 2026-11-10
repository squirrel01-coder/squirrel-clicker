"""Чистая выгрузка модели для 3ds Max (FBX).
Запуск: python export_max.py <скрипт_модели.py> <папка_с_geom.py> <папка_вывода> <ИмяФайла>
- детали одного вида объединяются в один объект (стены, перемычки, рамы окон, кровля...);
- объекты разложены по группам-родителям: UY / HOVLI / O'SIMLIKLAR / ATROF;
- у каждой сетки развёртка UV «кубом» 1 UV = 1 м (текстуры в реальном размере);
- начало координат 0,0,0 = пересечение осей 1 и А, отметка ±0.000 (чистый пол).
"""
import sys, runpy, re, bpy, bmesh
from collections import defaultdict
script, sk, out, fname = sys.argv[1:5]
sys.argv = [script, "--", sk, out, "test", "none"]
runpy.run_path(script, run_name="__main__")

GROUPS = {"Uy": "UY (dom)", "Hovli": "HOVLI (uchastka)", "O'simliklar": "O'SIMLIKLAR (ozelenenie)", "Atrof": "ATROF (sosednie doma)"}

def box_uv(me):
    bm = bmesh.new(); bm.from_mesh(me)
    uv = bm.loops.layers.uv.verify()
    for f in bm.faces:
        n = f.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        for l in f.loops:
            c = l.vert.co
            l[uv].uv = (c.y, c.z) if ax == 0 else (c.x, c.z) if ax == 1 else (c.x, c.y)
    bm.to_mesh(me); bm.free()

def category(name):
    m = re.match(r"[A-Za-zА-Яа-я' ]+", name)
    return (m.group(0).strip() if m else name) or name

# 1) сделать геометрию «настоящей»: модификаторы применить, траву-рассеивание убрать
dg = bpy.context.evaluated_depsgraph_get()
for o in list(bpy.data.objects):
    if o.type != "MESH": continue
    if any(m.type == "NODES" for m in o.modifiers):
        for m in list(o.modifiers):
            if m.type == "NODES": o.modifiers.remove(m)
    if o.modifiers:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(bpy.context.evaluated_depsgraph_get()))
        o.modifiers.clear(); o.data = me

result = []
for cname, gname in GROUPS.items():
    col = bpy.data.collections.get(cname)
    if not col: continue
    parent = bpy.data.objects.new(gname, None); bpy.context.scene.collection.objects.link(parent)
    buckets = defaultdict(list)
    for o in col.objects:
        if o.type == "MESH" and not o.hide_render:
            buckets[category(o.name)].append(o)
    for cat, objs in buckets.items():
        # объединение через bmesh в мировых координатах, материалы сохраняются
        me = bpy.data.meshes.new(cat); bm = bmesh.new(); mats = []
        for o in objs:
            tmp = o.data.copy(); tmp.transform(o.matrix_world)
            idx = []
            for s in o.material_slots:
                if s.material not in mats: mats.append(s.material)
                idx.append(mats.index(s.material))
            tb = bmesh.new(); tb.from_mesh(tmp)
            for f in tb.faces:
                if idx: f.material_index = idx[min(f.material_index, len(idx) - 1)]
            tb.to_mesh(tmp); tb.free()
            bm.from_mesh(tmp); bpy.data.meshes.remove(tmp)
        bm.to_mesh(me); bm.free()
        for m in mats: me.materials.append(m)
        box_uv(me)
        no = bpy.data.objects.new(f"{cat}", me); bpy.context.scene.collection.objects.link(no)
        no.parent = parent
        result.append((gname, cat, len(objs), len(me.polygons)))
        for o in objs: bpy.data.objects.remove(o, do_unlink=True)

# всё лишнее (исходники рассеивания, свет, сетки вне групп) убрать
keep = {o for o in bpy.data.objects if o.parent or o.name in GROUPS.values() or o.type == "CAMERA"}
for o in list(bpy.data.objects):
    if o not in keep: bpy.data.objects.remove(o, do_unlink=True)

path = f"{out}/{fname}.fbx"
bpy.ops.export_scene.fbx(filepath=path, object_types={"EMPTY", "MESH", "CAMERA"}, use_mesh_modifiers=True,
                         apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE", path_mode="COPY", embed_textures=True)
print("FBX", path)
for r in result: print("OBJ", *r)
print("TOTAL objects", len(result), "faces", sum(r[3] for r in result))
