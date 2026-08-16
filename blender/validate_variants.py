"""Blender-side variant validation (SG8) — headless QA + optional renders.

Runs the *same* validation core as pytest/Jupyter (``graphtope.validate_io``)
inside Blender, so what the designer opens in Blender is what the suite
verified — plus, optionally, a rendered thumbnail per variant for visual QA.

Headless (CI / the notebook's closing loop):

    blender --background --python blender/validate_variants.py -- <dir> [--render <outdir>]

Writes ``<dir>/validation.json`` (identical schema to
``validate_io.validate_directory``) and exits non-zero if any variant fails.
Inside the Blender UI: edit CONFIG and Run Script.
"""

import sys

import bpy  # noqa: E402  (only importable inside Blender)

# --- CONFIG (for interactive use) ----------------------------------------
DIRECTORY = "/absolute/path/to/variants"   # <-- edit me
RENDER_TO = ""                             # optional thumbnail directory
# -------------------------------------------------------------------------


def _bootstrap():
    """Find the graphtope package from the repo root (blender's interpreter
    is not the project env)."""
    here = __file__.replace("\\", "/").rsplit("/blender/", 1)[0]
    for cand in (here, "/Users/arlav/GitHub/graphtope"):
        if cand and cand not in sys.path:
            sys.path.insert(0, cand)
    try:
        import graphtope  # noqa: F401
    except ImportError:
        sys.exit("graphtope not importable — run from the repo, or set PYTHONPATH")


def _render(obj_path: str, out_png: str):
    """Import one variant and render a simple three-quarter thumbnail."""
    bpy.ops.wm.read_homefile(use_empty=True)
    if hasattr(bpy.ops.wm, "obj_import"):
        bpy.ops.wm.obj_import(filepath=obj_path)
    else:
        bpy.ops.import_scene.obj(filepath=obj_path)
    obs = list(bpy.context.scene.objects)
    if not obs:
        return
    xs = [o.location.x for o in obs]
    ys = [o.location.y for o in obs]
    zs = [o.location.z for o in obs]
    cx, cy, cz = (sum(xs) / len(xs), sum(ys) / len(ys), sum(zs) / len(zs))
    span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)) or 10.0
    cam = bpy.data.cameras.new("cam")
    cam_obj = bpy.data.objects.new("cam", cam)
    bpy.context.scene.collection.objects.link(cam_obj)
    dist = span * 1.8
    cam_obj.location = (cx + dist * 0.8, cy - dist * 0.8, cz + dist * 0.55)
    import mathutils
    look = mathutils.Vector((cx, cy, cz)) - cam_obj.location
    rot = mathutils.Vector((0, 0, -1)).rotation_difference(look).to_matrix()
    cam_obj.rotation_euler = rot.to_euler()
    bpy.context.scene.camera = cam_obj
    bpy.context.scene.render.filepath = out_png
    bpy.context.scene.render.resolution_x = 720
    bpy.context.scene.render.resolution_y = 480
    bpy.ops.render.render(write_still=True)


def main(directory: str, render_to: str = ""):
    _bootstrap()
    from graphtope import validate_io
    out = validate_io.validate_directory(directory)
    if render_to:
        import os
        os.makedirs(render_to, exist_ok=True)
        for fn in out["reports"]:
            base = fn[:-4]
            try:
                _render(os.path.join(directory, fn),
                        os.path.join(render_to, base + ".png"))
            except Exception as e:                    # renders are QA, not gates
                out["reports"][fn]["render_error"] = str(e)
    import json
    with open(directory + "/validation.json", "w") as fh:
        json.dump(out, fh, indent=2)
    n_ok = sum(1 for r in out["reports"].values() if r["ok"])
    print(f"graphtope validate: {n_ok}/{out['variants']} variants ok")
    if not out["ok"]:
        sys.exit(1)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if argv:
        d = argv[0]
        r = ""
        if "--render" in argv:
            r = argv[argv.index("--render") + 1]
        main(d, r)
    else:
        main(DIRECTORY, RENDER_TO)
