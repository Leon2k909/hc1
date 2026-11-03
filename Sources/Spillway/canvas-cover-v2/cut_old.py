"""Temporary models for comparing the canvas cover: python cut_old.py. The map's models aren't touched.

Writes into Assets/models/compare_old/, in spillway_east.obj's own coordinates, so each draws where it is when placed at the origin:
- spillway_canvas_old: the old cover (every sw_tarp face) and its two straps (the rv_dark faces inside their bounds), to show the old
  one anywhere.
- spillway_east_dark_rest: every other rv_dark face of the east model. With the east model's sw_tarp and rv_dark slots hidden, it puts
  back everything but the old cover and straps, so the real spot can be shot as an install would leave it.
And hidden.vmat, which draws nothing and casts no shadow.
"""
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
SRC = os.path.join(ROOT, "Assets", "models", "maps", "spillway", "spillway_east.obj")
OUT = os.path.join(ROOT, "Assets", "models", "compare_old")
REMAP = {"sw_tarp": "materials/spillway/sw_tarp.vmat", "rv_dark": "materials/riverdale/rv_dark.vmat"}

v, vt, vn, cur = [], [], [], None
old, rest = [], []
for line in open(SRC):
    if line.startswith("v "):
        # The position, and the line itself to copy out.
        v.append([float(x) for x in line.split()[1:4]] + [line])
    elif line.startswith("vt "):
        vt.append(line)
    elif line.startswith("vn "):
        vn.append(line)
    elif line.startswith("usemtl"):
        cur = line.split()[1]
    elif line.startswith("f ") and cur in REMAP:
        corners = [tuple(int(x) for x in t.split("/")) for t in line.split()[1:]]
        if cur == "sw_tarp":
            old.append((cur, corners))
            continue
        # The straps: e 1498..1602, n -1772..-1639, z 128..220; this OBJ is (-e, z, n).
        inside = all(-1603 <= v[c[0] - 1][0] <= -1497 and 127.9 <= v[c[0] - 1][1] <= 220.1 and -1772.1 <= v[c[0] - 1][2] <= -1638.9 for c in corners)
        (old if inside else rest).append((cur, corners))
if sum(1 for m, _ in old if m == "sw_tarp") != 11520 or sum(1 for m, _ in old if m == "rv_dark") != 48:
    raise SystemExit(f"unexpected faces: {len(old)} old, {len(rest)} rest")


def write(name, faces):
    maps = ({}, {}, {})
    stores = ([], [], [])
    by_material = {}
    for material, corners in faces:
        out = []
        for c in corners:
            idx = []
            for k, (table, store) in enumerate(zip(maps, stores)):
                if c[k] not in table:
                    table[c[k]] = len(table) + 1
                    store.append(v[c[k] - 1][3] if k == 0 else (vt, vn)[k - 1][c[k] - 1])
                idx.append(table[c[k]])
            out.append("%d/%d/%d" % tuple(idx))
        by_material.setdefault(material, []).append("f " + " ".join(out) + "\n")
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name + ".obj"), "w", newline="\n") as h:
        h.write(f"# Cut from spillway_east.obj by Sources/Spillway/canvas-cover-v2/cut_old.py, for comparisons only\nmtllib {name}.mtl\n")
        for store in stores:
            h.writelines(store)
        for material, lines in by_material.items():
            h.write(f"usemtl {material}\n")
            h.writelines(lines)
    with open(os.path.join(OUT, name + ".mtl"), "w", newline="\n") as h:
        h.writelines(f"newmtl {m}\nKd 1 1 1\nd 1\n" for m in by_material)
    remaps = "\n".join(f'\t\t\t\t\t\t\t{{ from = "{m}.vmat" to = "{REMAP[m]}" }},' for m in by_material)
    with open(os.path.join(OUT, name + ".vmdl"), "w", newline="\n") as h:
        h.write(f"""<!-- kv3 encoding:text:version{{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d}} format:modeldoc29:version{{3cec427c-1b0e-4d48-a90a-0436f33a6041}} -->
{{
	rootNode =
	{{
		_class = "RootNode"
		children =
		[
			{{
				_class = "MaterialGroupList"
				children =
				[
					{{
						_class = "DefaultMaterialGroup"
						remaps =
						[
{remaps}
						]
						use_global_default = false
						global_default_material = ""
					}},
				]
			}},
			{{
				_class = "RenderMeshList"
				children =
				[
					{{
						_class = "RenderMeshFile"
						name = "{name}"
						filename = "models/compare_old/{name}.obj"
						import_translation = [ 0.0, 0.0, 0.0 ]
						import_rotation = [ 0.0, 0.0, 0.0 ]
						import_scale = 1.0
						align_origin_x_type = "None"
						align_origin_y_type = "None"
						align_origin_z_type = "None"
						parent_bone = ""
						import_filter = {{ exclude_by_default = false exception_list = [ ] }}
					}},
				]
			}},
		]
		model_archetype = ""
		primary_associated_entity = ""
		anim_graph_name = ""
		base_model_name = ""
	}}
}}
""")
    print(name, len(faces), "faces")


write("spillway_canvas_old", old)
write("spillway_east_dark_rest", rest)
with open(os.path.join(OUT, "hidden.vmat"), "w", newline="\n") as h:
    h.write("""// Draws nothing, and casts no shadow: hides a map model's slot in comparison shots only (Sources/Spillway/canvas-cover-v2).

Layer0
{
	shader "shaders/complex.shader"
	F_ALPHA_TEST 1
	g_flAlphaTestReference "0.5"
	TextureTranslucency "[0.0 0.0 0.0 1.0]"
	TextureColor "[0.0 0.0 0.0 1.0]"
	g_flMetalness "0.000"
	g_bFogEnabled "1"
}
""")
print("hidden.vmat")
