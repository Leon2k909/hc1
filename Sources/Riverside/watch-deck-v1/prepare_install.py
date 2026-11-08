"""Stage the Pad model without the old watch deck's render triangles, and keep what is needed to put them back.

Reads   Assets/models/maps/riverside/riverside_pad.obj          the merged Pad render mesh (collision hulls are other files)
        output/riverside/watch-deck-v1/legacy_deck_3bec244c.obj  the old deck as `riverside_map.watch_deck` drew it, made
                                                                 by legacy_deck.py from the generator that built the Pad
Writes  output/riverside/watch-deck-v1/install-before/           the Pad OBJ and ModelDoc and the scene as they are now
        output/riverside/watch-deck-v1/install-stage/riverside_pad.obj   the Pad OBJ without the old deck's triangles
        output/riverside/watch-deck-v1/install-plan.json         hashes and counts the installer and the revert check

Only face lines are dropped, byte for byte (the file is CRLF); the vertices stay where they are. The old deck is found
twice, by exact vertex fingerprint and by region, and both must give the same 812 triangles.
"""
from pathlib import Path
import collections, hashlib, json, sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).absolute().parents[3]
OUT = ROOT / 'output/riverside/watch-deck-v1'
PAD = ROOT / 'Assets/models/maps/riverside/riverside_pad.obj'
PAD_VMDL = ROOT / 'Assets/models/maps/riverside/riverside_pad.vmdl'
SCENE = ROOT / 'Assets/scenes/maps/Riverside/riverside.scene'
LEGACY = OUT / 'legacy_deck_3bec244c.obj'
EXPECT = 812


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def records(data):
    """ lines (bytes, endings kept) and the faces: (line index, paint, sorted rounded vertices, vertices in order) """
    lines = data.splitlines(keepends=True)
    vs = [tuple(round(float(x), 3) for x in l.split()[1:4]) for l in lines if l.startswith(b'v ')]
    paint, faces = '', []
    for i, l in enumerate(lines):
        if l.startswith(b'usemtl '):
            paint = l.split()[1].decode()
        elif l.startswith(b'f '):
            pts = [vs[int(t.split(b'/')[0]) - 1] for t in l.split()[1:]]
            faces.append((i, paint, tuple(sorted(pts)), pts))
    return lines, faces


def in_deck_region(pts):
    """ OBJ axes are (-e, z, n): the deck's plan box e 5..115, n -580..-390 (the stair's foot is at -573), z 96..200 """
    return all(-115 <= x <= -5 and 96 <= y <= 200 and -580 <= z <= -390 for x, y, z in pts)


def main():
    plan_path = OUT / 'install-plan.json'
    before = OUT / 'install-before'
    assert not before.exists(), 'Already staged: revert.py first, or inspect install-before/ before staging again'
    _, legacy = records(LEGACY.read_bytes())
    wanted = collections.Counter((p, k) for _, p, k, _ in legacy)
    assert sum(wanted.values()) == EXPECT, sum(wanted.values())
    lines, faces = records(PAD.read_bytes())
    left, cut = collections.Counter(wanted), set()
    for i, p, k, _ in faces:
        if left[(p, k)]:
            cut.add(i)
            left[(p, k)] -= 1
    assert not +left, 'The Pad no longer holds the old deck exactly: %d missing' % sum(left.values())
    region = {i for i, p, k, pts in faces if in_deck_region(pts)}
    assert region == cut, ('Region and fingerprint disagree', len(region), len(cut))
    by_paint = collections.Counter(p for i, p, k, _ in faces if i in cut)
    before.mkdir(parents=True)
    for src, name in ((PAD, 'riverside_pad.obj'), (PAD_VMDL, 'riverside_pad.vmdl'), (SCENE, 'riverside.scene')):
        (before / name).write_bytes(src.read_bytes())
    stage = OUT / 'install-stage/riverside_pad.obj'
    stage.parent.mkdir(exist_ok=True)
    stage.write_bytes(b''.join(l for i, l in enumerate(lines) if i not in cut))
    manifest = json.loads((OUT / 'manifest.json').read_text())
    plan = dict(source=PAD.relative_to(ROOT).as_posix(), source_before=sha(PAD), source_after=sha(stage),
                staged=stage.relative_to(ROOT).as_posix(), removed_triangles=len(cut), removed_by_paint=dict(by_paint),
                pad_vmdl=sha(PAD_VMDL), scene_before=sha(SCENE), model=manifest['resource'],
                position=manifest['position'], triangles=manifest['triangles'],
                backup=before.relative_to(ROOT).as_posix())
    plan_path.write_text(json.dumps(plan, indent=2))
    print(json.dumps(plan, indent=2))


if __name__ == '__main__':
    main()
