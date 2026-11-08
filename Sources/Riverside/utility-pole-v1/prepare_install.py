"""Stage the Riverside dressing mesh without the nine old utility poles' shafts, crossarms and braces, and keep what is needed
to put them back.

Reads   Assets/models/maps/riverside/riverside_dressing.obj     the merged dressing render mesh (collision hulls are other files)
        output/riverside/utility-pole-v1/legacy_poles.obj        the old poles as `riverside_parts.pole` draws them (legacy_poles.py)
Writes  output/riverside/utility-pole-v1/install-before/         the dressing OBJ and ModelDoc and the scene as they are now
        output/riverside/utility-pole-v1/install-stage/riverside_dressing.obj   the dressing OBJ without the old poles' triangles
        output/riverside/utility-pole-v1/install-plan.json      hashes and counts the installer and the revert check

Only face lines are dropped, byte for byte; the vertices stay where they are. The old poles are found twice, by exact vertex
fingerprint and by region (a column round each pole's axis, rs_pole / rs_steel only), and the fingerprint's faces must be
exactly the 1116 triangles legacy_poles.py drew. Faces in a pole's column that are not in the fingerprint are reported (they
stay: they are the transformer cans' and lamp arms' own).
"""
from pathlib import Path
import collections, hashlib, json, sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).absolute().parents[3]
sys.path.insert(0, str(ROOT / 'Tools'))
OUT = ROOT / 'output/riverside/utility-pole-v1'
DRESSING = ROOT / 'Assets/models/maps/riverside/riverside_dressing.obj'
DRESSING_VMDL = ROOT / 'Assets/models/maps/riverside/riverside_dressing.vmdl'
SCENE = ROOT / 'Assets/scenes/maps/Riverside/riverside.scene'
LEGACY = OUT / 'legacy_poles.obj'
EXPECT = 1116


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


def pole_columns():
    """ (OBJ x, OBJ z, base height, height) of each old pole: OBJ axes are (-e, z, n) """
    import riverside_map as R
    out = []
    for c in R.POLES_WEST:
        out.append((-c[0], c[1], c[2], 430.0))
    for c in R.POLES_EAST:
        out.append((-c[0], c[1], c[2], 400.0))
    return out


def in_a_pole_column(pts, columns):
    for x0, z0, b, h in columns:
        if all(abs(x - x0) <= 60 and abs(z - z0) <= 60 and b - 1 <= y <= b + h + 4 for x, y, z in pts):
            return True
    return False


def main():
    plan_path = OUT / 'install-plan.json'
    before = OUT / 'install-before'
    assert not before.exists(), 'Already staged: revert.py first, or inspect install-before/ before staging again'
    _, legacy = records(LEGACY.read_bytes())
    wanted = collections.Counter((p, k) for _, p, k, _ in legacy)
    assert sum(wanted.values()) == EXPECT, sum(wanted.values())
    lines, faces = records(DRESSING.read_bytes())
    left, cut = collections.Counter(wanted), set()
    for i, p, k, _ in faces:
        if left[(p, k)]:
            cut.add(i)
            left[(p, k)] -= 1
    assert not +left, 'The dressing mesh no longer holds the old poles exactly: %d missing' % sum(left.values())
    columns = pole_columns()
    region = {i for i, p, k, pts in faces if p in ('rs_pole', 'rs_steel') and in_a_pole_column(pts, columns)}
    assert cut <= region, ('Fingerprint faces outside the pole columns', len(cut - region))
    extra = region - cut
    by_paint = collections.Counter(p for i, p, k, _ in faces if i in cut)
    extra_by_paint = collections.Counter(p for i, p, k, _ in faces if i in extra)
    if '--check' in sys.argv:
        print('--check: nothing written. fingerprint faces:', len(cut), dict(by_paint), '| in the pole columns but not drawn by pole():',
              len(extra), dict(extra_by_paint))
        return
    before.mkdir(parents=True)
    for src, name in ((DRESSING, 'riverside_dressing.obj'), (DRESSING_VMDL, 'riverside_dressing.vmdl'), (SCENE, 'riverside.scene')):
        (before / name).write_bytes(src.read_bytes())
    stage = OUT / 'install-stage/riverside_dressing.obj'
    stage.parent.mkdir(exist_ok=True)
    stage.write_bytes(b''.join(l for i, l in enumerate(lines) if i not in cut))
    manifest = json.loads((OUT / 'manifest.json').read_text())
    plan = dict(source=DRESSING.relative_to(ROOT).as_posix(), source_before=sha(DRESSING), source_after=sha(stage),
                staged=stage.relative_to(ROOT).as_posix(), removed_triangles=len(cut), removed_by_paint=dict(by_paint),
                left_in_pole_columns=dict(extra_by_paint), dressing_vmdl=sha(DRESSING_VMDL), scene_before=sha(SCENE),
                models={k: manifest[k]['resource'] for k in ('pole_2arm', 'pole_1arm')}, backup=before.relative_to(ROOT).as_posix())
    plan_path.write_text(json.dumps(plan, indent=2))
    print(json.dumps(plan, indent=2))


if __name__ == '__main__':
    main()
