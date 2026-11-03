"""The old slab pallet as a model of its own, for comparisons only: python cut_old.py

Copies the faces drawn with rv_desk (only the slabs use it) out of spillway_cargo.obj into Assets/models/compare_old/spillway_slabs.*,
in the map model's own coordinates, so at the origin it draws exactly where the slabs are. The map model isn't touched.
"""
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
SRC = os.path.join(ROOT, "Assets", "models", "maps", "spillway", "spillway_cargo.obj")
OUT = os.path.join(ROOT, "Assets", "models", "compare_old")
NAME = "spillway_slabs"

v, vt, vn, faces, cur = [], [], [], [], None
for line in open(SRC):
    if line.startswith("v "):
        v.append(line)
    elif line.startswith("vt "):
        vt.append(line)
    elif line.startswith("vn "):
        vn.append(line)
    elif line.startswith("usemtl"):
        cur = line.split()[1]
    elif line.startswith("f ") and cur == "rv_desk":
        faces.append([tuple(int(x) for x in t.split("/")) for t in line.split()[1:]])
maps = ({}, {}, {})
lines = ([], [], [])
out_faces = []
for f in faces:
    corner = []
    for c in f:
        idx = []
        for k, (table, store, source) in enumerate(zip(maps, lines, (v, vt, vn))):
            if c[k] not in table:
                table[c[k]] = len(table) + 1
                store.append(source[c[k] - 1])
            idx.append(table[c[k]])
        corner.append("%d/%d/%d" % tuple(idx))
    out_faces.append("f " + " ".join(corner) + "\n")
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, NAME + ".obj"), "w", newline="\n") as h:
    h.write(f"# The old slab pallet cut from spillway_cargo.obj by Sources/Spillway/cargo-props-v2/cut_old.py, for comparisons only\nmtllib {NAME}.mtl\n")
    for block in lines:
        h.writelines(block)
    h.write("usemtl rv_desk\n")
    h.writelines(out_faces)
with open(os.path.join(OUT, NAME + ".mtl"), "w", newline="\n") as h:
    h.write("newmtl rv_desk\nKd 1 1 1\nd 1\n")
with open(os.path.join(OUT, NAME + ".vmdl"), "w", newline="\n") as h:
    h.write("""<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{
	rootNode =
	{
		_class = "RootNode"
		children =
		[
			{
				_class = "MaterialGroupList"
				children =
				[
					{
						_class = "DefaultMaterialGroup"
						remaps =
						[
							{ from = "rv_desk.vmat" to = "materials/riverdale/rv_desk.vmat" },
						]
						use_global_default = false
						global_default_material = ""
					},
				]
			},
			{
				_class = "RenderMeshList"
				children =
				[
					{
						_class = "RenderMeshFile"
						name = "spillway_slabs"
						filename = "models/compare_old/spillway_slabs.obj"
						import_translation = [ 0.0, 0.0, 0.0 ]
						import_rotation = [ 0.0, 0.0, 0.0 ]
						import_scale = 1.0
						align_origin_x_type = "None"
						align_origin_y_type = "None"
						align_origin_z_type = "None"
						parent_bone = ""
						import_filter = { exclude_by_default = false exception_list = [ ] }
					},
				]
			},
		]
		model_archetype = ""
		primary_associated_entity = ""
		anim_graph_name = ""
		base_model_name = ""
	}
}
""")
print(len(out_faces), "faces,", len(lines[0]), "verts")
