"""Writes table.py from table_head.py.txt and the chair builder's shared stages, with an export that makes two models from one atlas. Run once from the project root; kept for the record."""
src = open("Sources/CerroBlanco/cafe-chair-v2/chair.py", encoding="utf-8").read()
head = open("Sources/CerroBlanco/cafe-table-v2/table_head.py.txt", encoding="utf-8").read()
tail = src[src.index("def harden_all():"):]


def swap(text, old, new):
    assert text.count(old) == 1, ("missing", old[:90])
    return text.replace(old, new)


a = tail.index("def share(finish, normal, centre):")
b = tail.index("def pack(mesh, pad_px=4):")
tail = tail[:a] + '''def share(finish, normal, centre):
    """How much texture an island gets, against the top's face at 1."""
    if finish == LAMINATE:
        if normal.z > 0.7:
            return 1.0
        if normal.z < -0.7:
            return 0.35
        return 1.2
    if normal.z < -0.7 and centre.z < 1.0:
        return 0.04
    if finish == STEEL:
        return 1.3
    return 0.9


''' + tail[b:]
for old, new in [
    ("chair_lod", "table_lod"), ("chair_edges.npy", "table_edges.npy"), ("chair_parts.json", "table_parts.json"), ('"chair.json"', '"table.json"'),
    ("chair_baked_uv_hash.txt", "table_baked_uv_hash.txt"), ("bake_ch_", "bake_tb_"), ("Sources/CerroBlanco/cafe-chair-v2/chair.py", "Sources/CerroBlanco/cafe-table-v2/table.py"),
    ("chair stages done", "table stages done"),
]:
    assert old in tail, old
    tail = tail.replace(old, new)
a = tail.index("            dict(density=density, range=POS_RANGE, seat_top=SEAT_TOP")
b = tail.index("\n", a)
tail = tail[:a] + "            dict(density=density, range=POS_RANGE, top=(TOP_Z, TOP_T, TOP_R, EASE), hub=(HUB_Z0, HUB_R), arms=(ARM_R0, ARM_R1, ARM_W, ARM_T), column=COLUMN_R, base_r=BASE_R, screws=SCREWS)," + tail[b:]

a = tail.index("def export_stage():")
b = tail.index('if "build" in STAGES:')
exp = tail[a:b]
exp = swap(exp, "    counts = {}\n    for number in (0, 1, 2):\n", '''    for model, leave_out in ((NAME, None), (f"{NAME}_top", PEDESTAL)):
        export_model(model, leave_out)
    with open(os.path.join(OUT, f"{NAME}.mtl"), "w", newline="\\n") as h:
        h.write(f"newmtl {NAME}\\nKd 1 1 1\\nd 1\\n")


def export_model(model, leave_out):
    """One model's LOD OBJs and vmdl, and for the whole table the material too. leave_out names parts whose faces it goes without."""
    rand_name = {round(r, 4): n for r, n, _ in json.load(open(os.path.join(WORK, "table_parts.json")))}
    counts = {}
    for number in (0, 1, 2):
''')
exp = swap(exp, '        mod = ob.modifiers.new("wn", "WEIGHTED_NORMAL")\n', '        mod = ob.modifiers.get("wn") or ob.modifiers.new("wn", "WEIGHTED_NORMAL")\n')
exp = swap(exp, '        em.corner_normals.foreach_get("vector", nn)\n', '''        em.corner_normals.foreach_get("vector", nn)
        fa = np.empty(n_loops * 4, np.float32)
        em.color_attributes["facts"].data.foreach_get("color", fa)
        tri_part = fa.reshape(-1, 4)[loops[0::3], 1]
        kept = np.array([rand_name.get(round(float(r), 4)) not in (leave_out or ()) for r in tri_part])
''')
exp = swap(exp, "        for k in range(n_tris):\n            tri = []\n", "        for k in range(n_tris):\n            if not kept[k]:\n                continue\n            tri = []\n")
exp = swap(exp, 'os.path.join(OUT, f"{NAME}_lod{number}.obj")', 'os.path.join(OUT, f"{model}_lod{number}.obj")')
exp = swap(exp, '''        counts[number] = n_tris
        print("lod", number, "tris", n_tris, flush=True)
''', '''        counts[number] = int(kept.sum())
        print(model, "lod", number, "tris", counts[number], flush=True)
''')
exp = swap(exp, '''    with open(os.path.join(OUT, f"{NAME}.mtl"), "w", newline="\\n") as h:
        h.write(f"newmtl {NAME}\\nKd 1 1 1\\nd 1\\n")
    meshes''', "    meshes")
exp = swap(exp, 'filename = "{FOLDER}/{NAME}_lod{l}.obj"', 'filename = "{FOLDER}/{model}_lod{l}.obj"')
exp = swap(exp, '''    with open(os.path.join(OUT, f"{NAME}.vmdl"), "w", newline="\\n") as h:
        h.write(doc)
''', '''    with open(os.path.join(OUT, f"{model}.vmdl"), "w", newline="\\n") as h:
        h.write(doc)
    if model != NAME:
        print("exported", model, counts, flush=True)
        return
''')
tail = tail[:a] + exp + tail[b:]
open("Sources/CerroBlanco/cafe-table-v2/table.py", "w", encoding="utf-8", newline="\n").write(head + tail)
print("table.py written")
