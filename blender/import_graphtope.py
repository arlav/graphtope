"""Import a graphtope OBJ massing into Blender, organised by space type.

`graphtope.exchange.to_obj(sg, path)` writes an OBJ (one object per space, named
by node id, with a colour `.mtl`) plus a `<path>.graph.json` sidecar that holds
the typed graph. This script imports that OBJ, colours each space by its τ type
and files it into a per-type collection.

Run inside Blender (Scripting workspace → Run Script), or:
    blender --python blender/import_graphtope.py

You can edit the imported massing (move / resize / add spaces), export back to
OBJ, and read it into a typed graph with
`graphtope.exchange.graph_from_obj(obj_path, sidecar_path)`.
"""

import json
import os

import bpy

# --- CONFIG -------------------------------------------------------------
OBJ = "/absolute/path/to/building.obj"   # <-- edit me (the file from exchange.to_obj)
# ------------------------------------------------------------------------

#: τ legend (§3.1) as Blender RGB 0..1
LEGEND = {
    "generic":   (0.227, 0.227, 0.227),
    "corridor":  (0.910, 0.510, 0.118),
    "staircase": (0.180, 0.545, 0.341),
    "u_section": (0.122, 0.435, 0.922),
    "l_section": (0.090, 0.745, 0.812),
    "entrance":  (0.753, 0.224, 0.169),
}


def _material(label):
    name = f"gt_{label}"
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = False
    m.diffuse_color = (*LEGEND.get(label, (0.5, 0.5, 0.5)), 1.0)
    return m


def _collection(name):
    c = bpy.data.collections.get(name)
    if not c:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def _load_types(obj_path):
    side = obj_path + ".graph.json"
    if not os.path.exists(side):
        return {}
    with open(side) as fh:
        data = json.load(fh)
    return {n["id"]: n["label"] for n in data["nodes"]}        # OBJ object name == node id


def _import(path):
    before = set(bpy.data.objects)
    if hasattr(bpy.ops.wm, "obj_import"):                       # Blender 4.x
        bpy.ops.wm.obj_import(filepath=path)
    else:                                                      # Blender 3.x
        bpy.ops.import_scene.obj(filepath=path)
    return [o for o in bpy.data.objects if o not in before]


def main():
    types = _load_types(OBJ)
    objs = _import(OBJ)
    for o in objs:
        label = types.get(o.name, "generic")
        if o.data:
            o.data.materials.clear()
            o.data.materials.append(_material(label))
        col = _collection(f"type_{label}")
        for c in list(o.users_collection):
            c.objects.unlink(o)
        col.objects.link(o)
    print(f"graphtope: imported {len(objs)} spaces, organised by type")


if __name__ == "__main__":
    main()
