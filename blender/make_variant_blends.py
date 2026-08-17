"""Build .blend files + colour-coded renders of graphtope variants.

Headless:

    blender --background --factory-startup \
        --python blender/make_variant_blends.py -- <variants_dir> <renders_dir> <blends_dir>

Per ``*.obj`` in ``variants_dir``: the geometry is built **directly from the
``.graph.json`` sidecar** (the authoritative graph — each boxed node becomes
a named cube; no OBJ-importer quirks, one object per room guaranteed),
coloured by its room kind (Σ_int subtypes first, then the τ block legend),
filed into per-type collections, staged on a ground plane with a sun + area
fill and a fitted three-quarter aerial camera (Track To constraint), rendered
(Cycles, denoised) and saved as a standalone ``.blend``.

Assumes the exports were validated (``graphtope.validate_io``) — this renders,
it does not check.
"""

import json
import math
import os
import sys

import bpy
import mathutils

# --- colours (hex) — Σ_int room kinds first, then the τ block legend ------
COLOURS = {
    # interior subtypes (SG1 registry)
    "living":   "#E8A33D", "sleeping": "#4C78A8", "kitchen":  "#E4572E",
    "bath":     "#54B3A5", "wc":       "#9D7BB0", "loggia":   "#72B742",
    "storage":  "#8C6D4F", "entry":    "#F58518", "void":     "#EDEDED",
    "room":     "#B279A2", "door":     "#3A3A3A", "window":   "#9ECCE3",
    # block labels (τ legend)
    "corridor": "#E8960F", "staircase": "#2CA02C", "entrance": "#C43A2F",
    "generic":  "#8A8A8A", "u_section": "#1F6EB2", "l_section": "#17BEC4",
}
DEFAULT_COLOUR = "#B0B0B0"
BOX_KEYS = ("x", "y", "z", "w", "d", "h")


def _lin(hexstr):
    h = hexstr.lstrip("#")
    return tuple((int(h[i:i + 2], 16) / 255.0) ** 2.2 for i in (0, 2, 4))


def _material(kind):
    key = f"gt_{kind}"
    m = bpy.data.materials.get(key)
    if m:
        return m
    m = bpy.data.materials.new(key)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*_lin(COLOURS.get(kind,
                                                                 DEFAULT_COLOUR)), 1.0)
    bsdf.inputs["Roughness"].default_value = 0.7
    bsdf.inputs["Specular IOR Level" ].default_value = 0.2 if "Specular IOR Level" in bsdf.inputs else 0.2
    return m


def _kind_of(node):
    sub = node.get("attrs", {}).get("subtype")
    return sub if sub in COLOURS else node["label"]


def build(sidecar_path, png_path, blend_path):
    bpy.ops.wm.read_homefile(use_empty=True)
    scene = bpy.context.scene
    with open(sidecar_path) as fh:
        data = json.load(fh)

    root = bpy.data.collections.new("variant")
    scene.collection.children.link(root)
    per_type: dict = {}

    for n in data["nodes"]:
        a = n.get("attrs", {})
        if not all(k in a for k in BOX_KEYS):
            continue
        x, y, z, w, d, h = (a[k] for k in BOX_KEYS)
        kind = _kind_of(n)
        bpy.ops.mesh.primitive_cube_add(size=1.0,
                                        location=(x + w / 2, y + d / 2, z + h / 2))
        o = bpy.context.active_object
        o.name = n["id"]
        o.scale = (max(w, 0.05), max(d, 0.05), max(h, 0.05))
        bpy.ops.object.transform_apply(scale=True)
        o.data.materials.append(_material(kind))
        col = per_type.get(kind)
        if col is None:
            col = bpy.data.collections.new(kind)
            root.children.link(col)
            per_type[kind] = col
        scene.collection.objects.unlink(o)
        col.objects.link(o)

    boxes = [n for n in data["nodes"] if all(k in n.get("attrs", {}) for k in BOX_KEYS)]
    lo = [min(n["attrs"][k] for n in boxes) for k in ("x", "y", "z")]
    hi = [max(n["attrs"][k] + n["attrs"][k2] for n in boxes)
          for k, k2 in (("x", "w"), ("y", "d"), ("z", "h"))]
    centre = [(lo[i] + hi[i]) / 2 for i in range(3)]
    span = max(hi[i] - lo[i] for i in range(3)) or 10.0
    # bounding-sphere radius: guarantees corners stay in frame for wide slabs
    radius = 0.5 * sum((hi[i] - lo[i]) ** 2 for i in range(3)) ** 0.5

    # -- ground plane ------------------------------------------------------
    bpy.ops.mesh.primitive_plane_add(size=span * 3.2,
                                     location=(centre[0], centre[1], lo[2] - 0.03))
    ground = bpy.context.active_object
    ground.data.materials.append(_material("ground"))
    ground.name = "ground"
    root.objects.link(ground)
    scene.collection.objects.unlink(ground)

    # -- camera: fitted aerial, aimed by constraint -------------------------
    target = bpy.data.objects.new("target", None)
    target.location = mathutils.Vector(centre)
    root.objects.link(target)

    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = 50
    cam = bpy.data.objects.new("cam", cam_data)
    elev, azim = math.radians(30), math.radians(-52)
    direction = mathutils.Vector((math.cos(elev) * math.cos(azim),
                                  math.cos(elev) * math.sin(azim),
                                  math.sin(elev)))
    dist = radius / math.sin(math.radians(12.5)) * 1.15   # 25° half-FOV
    cam.location = mathutils.Vector(centre) + direction * dist
    scene.collection.objects.link(cam)
    con = cam.constraints.new("TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    scene.camera = cam
    scene.view_layers[0].update()

    # -- lights: key sun, warm fill, soft world -----------------------------
    sun_data = bpy.data.lights.new("sun", "SUN")
    sun_data.energy = 3.0
    sun_data.angle = math.radians(10)
    sun = bpy.data.objects.new("sun", sun_data)
    sun.rotation_euler = (math.radians(55), math.radians(8), math.radians(30))
    root.objects.link(sun)

    fill_data = bpy.data.lights.new("fill", "AREA")
    fill_data.energy = max(300.0, span * span * 2.0)
    fill_data.size = span * 1.6
    fill = bpy.data.objects.new("fill", fill_data)
    fill.location = (mathutils.Vector(centre)
                     + mathutils.Vector((-0.7, 0.9, 0.6)).normalized() * span * 1.3)
    con = fill.constraints.new("TRACK_TO")
    con.target = target
    con.track_axis = "TRACK_NEGATIVE_Z"
    con.up_axis = "UP_Y"
    root.objects.link(fill)

    world = bpy.data.worlds.new("world")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (*_lin("#E6EAF0"), 1.0)
    bg.inputs[1].default_value = 0.6
    scene.world = world

    # -- render ------------------------------------------------------------
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 96
    scene.cycles.use_denoising = True
    scene.render.resolution_x = 1280
    scene.render.resolution_y = 960
    scene.render.filepath = png_path
    scene.render.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)

    bpy.ops.wm.save_as_mainfile(filepath=blend_path)


def main(variants_dir, renders_dir, blends_dir):
    os.makedirs(renders_dir, exist_ok=True)
    os.makedirs(blends_dir, exist_ok=True)
    names = sorted(f for f in os.listdir(variants_dir)
                   if f.endswith(".graph.json"))
    for fn in names:
        base = fn[:-len(".graph.json")]
        print(f"graphtope render: {base}", flush=True)
        build(os.path.join(variants_dir, fn),
              os.path.join(renders_dir, base + ".png"),
              os.path.join(blends_dir, base + ".blend"))
    print(f"graphtope render: done — {len(names)} variants")


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(argv) < 3:
        sys.exit("usage: blender --background --python "
                 "make_variant_blends.py -- <variants> <renders> <blends>")
    main(*argv[:3])
