"""Installs the guard huts into the live Riverdale map (and reverts), without regenerating the area models (the live OBJs carry cuts and edits the generator does not know).

python -X utf8 install.py plan  <old_stage> <new_stage>   list the faces the new generator no longer draws (old-state minus new-state staged riverdale_west/east.obj)
python -X utf8 install.py apply <old_stage> <new_stage>   cut exactly those face lines from the live OBJs, insert the 'Guard Huts' scene group, write install_state.json
python -X utf8 install.py revert                           put every cut line back (from install_state.json) and remove the group

Face identity = material + the three/four corner positions (the vertex numbering differs between builds). Vertex lines are never touched. CRLF/LF are preserved.
"""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K  # noqa: E402
import riverdale_huts as HUTS  # noqa: E402

LIVE = ROOT / "Assets" / "models" / "maps" / "riverdale"
SCENE = ROOT / "Assets" / "scenes" / "maps" / "Riverdale" / "riverdale.scene"
AREAS = ("riverdale_west", "riverdale_east")
STATE = HERE / "install_state.json"
SEED = "9c41e7d2-3b58-4f0a-b6d1-27a8e5c04f93"


def keyed_faces(raw):
    """ ( list of ( line index, key ) for every f line ) of an OBJ as bytes. """
    verts = []
    out = []
    mtl = None
    lines = raw.split(b"\n")
    for i, line in enumerate(lines):
        if line.startswith(b"v "):
            p = line.split()
            verts.append((round(float(p[1]), 3), round(float(p[2]), 3), round(float(p[3]), 3)))
        elif line.startswith(b"usemtl"):
            mtl = line.split(None, 1)[1].strip()
        elif line.startswith(b"f "):
            idx = [int(t.split(b"/")[0]) for t in line.split()[1:]]
            corners = tuple(verts[(j - 1) if j > 0 else len(verts) + j] for j in idx)
            out.append((i, (mtl, corners)))
    return lines, out


def find(stage, name):
    hits = list(Path(stage).rglob(name + ".obj"))
    assert len(hits) == 1, (name, hits)
    return hits[0]


def removed_keys(old_stage, new_stage, name):
    _, old = keyed_faces(find(old_stage, name).read_bytes())
    _, new = keyed_faces(find(new_stage, name).read_bytes())
    co, cn = Counter(k for _, k in old), Counter(k for _, k in new)
    gone, added = co - cn, cn - co
    return gone, added


def plan(old_stage, new_stage):
    for name in AREAS:
        gone, added = removed_keys(old_stage, new_stage, name)
        by_mtl = Counter()
        for (mtl, _), n in gone.items():
            by_mtl[mtl.decode()] += n
        print(name, "faces removed", sum(gone.values()), "added", sum(added.values()), dict(by_mtl))


def group_text():
    ids = K.SceneIds(SEED)
    return HUTS.scene_group(ids, placed=PLACED_FIXED)


# The two placements (world x, y, z, yaw): he = f * -2120, plan centre (he, -1450) -> world (-1450, -he, 0).
PLACED_FIXED = [
    (HUTS.MODELS[1], (-1450.0, 2120.0, 0.0), 0.0),    # f = +1, he = -2120, east-facing window
    (HUTS.MODELS[-1], (-1450.0, -2120.0, 0.0), 0.0),  # f = -1, he = +2120, west-facing window
]


def scene_insert(raw):
    text = raw.decode("utf8")
    assert "Guard Huts" not in text
    group = json.dumps(group_text(), indent=2)
    block = "\r\n".join(" " * 8 + ln for ln in group.split("\n"))
    li = text.index('"Name": "Lights"')
    tail = '\r\n      ]\r\n    },\r\n    {\r\n      "__guid"'
    pos = text.rfind(tail, 0, li)
    assert pos > 0 and text[pos - 9:pos] == "        }", repr(text[pos - 12:pos])
    return (text[:pos] + ",\r\n" + block + text[pos:]).encode("utf8")


def apply(old_stage, new_stage):
    state = {"areas": {}, "scene": {}}
    for name in AREAS:
        gone, added = removed_keys(old_stage, new_stage, name)
        assert not added, ("the hook added faces", name, sum(added.values()))
        path = LIVE / (name + ".obj")
        raw = path.read_bytes()
        lines, faces = keyed_faces(raw)
        need = Counter(gone)
        cut = []
        for i, key in faces:
            if need[key] > 0:
                need[key] -= 1
                cut.append(i)
        assert sum(need.values()) == 0, ("faces not found in the live file", name, sum(need.values()))
        state["areas"][name] = {"sha1_before": hashlib.sha1(raw).hexdigest(), "bytes_before": len(raw),
                                "removed": [[i, lines[i].decode("latin-1")] for i in cut]}
        cutset = set(cut)
        out = b"\n".join(ln for i, ln in enumerate(lines) if i not in cutset)
        path.write_bytes(out)
        state["areas"][name]["sha1_after"] = hashlib.sha1(out).hexdigest()
        print(name, "cut", len(cut), "face lines;", len(raw), "->", len(out), "bytes")
    raw = SCENE.read_bytes()
    state["scene"] = {"sha1_before": hashlib.sha1(raw).hexdigest(), "bytes_before": len(raw)}
    new = scene_insert(raw)
    SCENE.write_bytes(new)
    state["scene"]["sha1_after"] = hashlib.sha1(new).hexdigest()
    STATE.write_text(json.dumps(state), encoding="utf8")
    print("scene", len(raw), "->", len(new), "bytes; state saved")


def revert():
    state = json.loads(STATE.read_text(encoding="utf8"))
    for name, rec in state["areas"].items():
        path = LIVE / (name + ".obj")
        lines = path.read_bytes().split(b"\n")
        for i, ln in rec["removed"]:                      # ascending: each index is its place in the original file
            lines.insert(i, ln.encode("latin-1"))
        out = b"\n".join(lines)
        assert hashlib.sha1(out).hexdigest() == rec["sha1_before"], ("reverted file differs", name)
        path.write_bytes(out)
        print(name, "restored", len(rec["removed"]), "lines, sha1 matches")
    raw = SCENE.read_bytes()
    text = raw.decode("utf8")
    i = text.index('"Name": "Guard Huts"')
    start = text.rfind(",\r\n        {", 0, i)
    tail = '\r\n      ]\r\n    },\r\n    {\r\n      "__guid"'
    end = text.index(tail, i)
    out = (text[:start] + text[end:]).encode("utf8")
    assert hashlib.sha1(out).hexdigest() == state["scene"]["sha1_before"], "reverted scene differs"
    SCENE.write_bytes(out)
    print("scene restored, sha1 matches")


def remove_group(text):
    i = text.index('"Name": "Guard Huts"')
    start = text.rfind(",\r\n        {", 0, i)
    tail = '\r\n      ]\r\n    },\r\n    {\r\n      "__guid"'
    end = text.index(tail, i)
    return text[:start] + text[end:]


def regroup():
    """ Replace the installed scene group with the current riverdale_huts.scene_group (the OBJ cuts stay). """
    state = json.loads(STATE.read_text(encoding="utf8"))
    base = remove_group(SCENE.read_bytes().decode("utf8")).encode("utf8")
    assert hashlib.sha1(base).hexdigest() == state["scene"]["sha1_before"], "scene changed under the group"
    new = scene_insert(base)
    SCENE.write_bytes(new)
    state["scene"]["sha1_after"] = hashlib.sha1(new).hexdigest()
    STATE.write_text(json.dumps(state), encoding="utf8")
    print("scene group replaced;", len(base), "->", len(new), "bytes")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "plan":
        plan(*sys.argv[2:4])
    elif cmd == "apply":
        apply(*sys.argv[2:4])
    elif cmd == "regroup":
        regroup()
    elif cmd == "revert":
        revert()
    else:
        sys.exit(__doc__)
