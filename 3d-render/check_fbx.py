import bpy, sys
from mathutils import Vector
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=sys.argv[1])
for n in ("Devor", "Tom", "Ayvon pol"):
    o = next(o for o in bpy.data.objects if o.name.startswith(n) and o.parent and o.parent.name.startswith("UY"))
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    mn = [min(p[i] for p in pts) for i in range(3)]; mx = [max(p[i] for p in pts) for i in range(3)]
    print(n, "мин", [round(v, 3) for v in mn], "макс", [round(v, 3) for v in mx])
print("parents", sorted({o.parent.name for o in bpy.data.objects if o.parent}))
