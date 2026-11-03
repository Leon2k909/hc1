"""Writes machine.py from machine_head.py.txt and the chair builder's shared stages (one model). Run once from the project root; kept for the record."""
src = open("Sources/CerroBlanco/cafe-chair-v2/chair.py", encoding="utf-8").read()
head = open("Sources/CerroBlanco/espresso-machine-v2/machine_head.py.txt", encoding="utf-8").read()
tail = src[src.index("def harden_all():"):]

a = tail.index("def share(finish, normal, centre):")
b = tail.index("def pack(mesh, pad_px=4):")
tail = tail[:a] + '''def share(finish, normal, centre):
    """How much texture an island gets, against a side panel at 1. Half the boxes' area is hidden: the body and head behind the side panels, the tops under the cup warmer, its underside,
    the base pan under the body and the drip tray, and the machine's underside. Those get next to none."""
    if normal.z < -0.7 and centre.z < BASE_Z + 0.5:
        return 0.03
    if abs(normal.y) > 0.7 and abs(abs(centre.y) - (HALF_W - 0.8)) < 0.12 and centre.x < HEAD_X + 0.2:
        return 0.04
    if abs(normal.z) > 0.7 and (abs(centre.z - TOP_Z) < 0.05 or abs(centre.z - (BASE_Z + 0.8)) < 0.05):
        return 0.04
    if finish == GAUGE:
        return 3.2 if normal.x > 0.5 else 0.3
    if finish == BLACK:
        return 1.2
    if finish in (PORCELAIN, RUBBER):
        return 0.6
    return 1.0


''' + tail[b:]
for old, new in [
    ("chair_lod", "machine_lod"), ("chair_edges.npy", "machine_edges.npy"), ("chair_parts.json", "machine_parts.json"), ('"chair.json"', '"machine.json"'),
    ("chair_baked_uv_hash.txt", "machine_baked_uv_hash.txt"), ("bake_ch_", "bake_em_"), ("Sources/CerroBlanco/cafe-chair-v2/chair.py", "Sources/CerroBlanco/espresso-machine-v2/machine.py"),
    ("chair stages done", "machine stages done"), ("(0.0, 30.0, 80.0)", "(0.0, 20.0, 60.0)"),
]:
    assert old in tail, old
    tail = tail.replace(old, new)
a = tail.index("            dict(density=density, range=POS_RANGE, seat_top=SEAT_TOP")
b = tail.index("\n", a)
tail = tail[:a] + "            dict(density=density, range=POS_RANGE, half_w=HALF_W, back_x=BACK_X, front_x=FRONT_X, head=(HEAD_X, HEAD_Z), base_z=BASE_Z, top_z=TOP_Z, group=(GROUP_X, GROUP_Y), wand_y=WAND_Y, tray_x=TRAY_X, gauges=GAUGES)," + tail[b:]
open("Sources/CerroBlanco/espresso-machine-v2/machine.py", "w", encoding="utf-8", newline="\n").write(head + tail)
print("machine.py written")
