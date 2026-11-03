"""Writes cup.py from cup_head.py.txt and the table builder's shared stages (its two-model export included). Run once from the project root; kept for the record."""
src = open("Sources/CerroBlanco/cafe-table-v2/table.py", encoding="utf-8").read()
head = open("Sources/CerroBlanco/cafe-cup-v2/cup_head.py.txt", encoding="utf-8").read()
tail = src[src.index("def harden_all():"):]


def swap(text, old, new):
    assert text.count(old) == 1, ("missing", old[:90])
    return text.replace(old, new)


head = swap(head, "PORCELAIN, COFFEE, STEEL = 0, 1, 4\n", "PORCELAIN, POWDER, CAST, STEEL, COFFEE = 0, 1, 2, 4, 5  # POWDER and CAST aren't used: the shared stages look for them.\n")
head = swap(head, '''    n = len(path)
    widths = [0.44 - 0.1 * math.sin(math.pi * k / (n - 1)) for k in range(n)]
    thick = [0.26 - 0.06 * math.sin(math.pi * k / (n - 1)) for k in range(n)]
    # strip() lays its width across the path and its thickness in the path's own plane: here width runs along y.
    strip(piece(PORCELAIN, 3, name="handle"), path, widths, thick, 10)
''', '''    n = len(path)
    # The tube's width runs across the loop's plane (y), its thickness, flattened, in it: a strap, slimmer at its middle.
    tube(piece(PORCELAIN, 3, name="handle"), path, [0.22 - 0.05 * math.sin(math.pi * k / (n - 1)) for k in range(n)], 10, flatten=0.6)
''')
a = tail.index("def share(finish, normal, centre):")
b = tail.index("def pack(mesh, pad_px=4):")
tail = tail[:a] + '''def share(finish, normal, centre):
    """How much texture an island gets, against the saucer's top at 1."""
    if finish == COFFEE:
        return 1.4 if normal.z > 0.5 else 0.1
    if finish == PORCELAIN and normal.z < -0.6 and centre.z < 0.3:
        return 0.3
    return 1.0


''' + tail[b:]
for old, new in [
    ("table_lod", "cup_lod"), ("table_edges.npy", "cup_edges.npy"), ("table_parts.json", "cup_parts.json"), ('"table.json"', '"cup.json"'),
    ("table_baked_uv_hash.txt", "cup_baked_uv_hash.txt"), ("bake_tb_", "bake_cu_"), ("Sources/CerroBlanco/cafe-table-v2/table.py", "Sources/CerroBlanco/cafe-cup-v2/cup.py"),
    ("table stages done", "cup stages done"), ("(0.0, 30.0, 80.0)", "(0.0, 10.0, 30.0)"),
]:
    assert old in tail, old
    tail = tail.replace(old, new)
a = tail.index("            dict(density=density, range=POS_RANGE, top=(TOP_Z, TOP_T, TOP_R, EASE)")
b = tail.index("\n", a)
tail = tail[:a] + "            dict(density=density, range=POS_RANGE, well=WELL_Z, cup_z=CUP_Z, coffee_z=COFFEE_Z, spoon_angle=SPOON_ANGLE, saucer=SAUCER, cup=CUP)," + tail[b:]
tail = swap(tail, '    for model, leave_out in ((NAME, None), (f"{NAME}_top", PEDESTAL)):\n', "    for model, leave_out in VARIANTS:\n")
open("Sources/CerroBlanco/cafe-cup-v2/cup.py", "w", encoding="utf-8", newline="\n").write(head + tail)
print("cup.py written")
