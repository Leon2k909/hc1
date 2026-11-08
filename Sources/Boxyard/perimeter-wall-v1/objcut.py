"""Split an OBJ written by Tools/map_kit.py into the faces of some materials and the rest.

map_kit writes one `o` object, all `v`, then all `vt`, then all `vn`, then `usemtl <paint>` blocks of triangles
`f a/a/n b/b/n c/c/n` (each polygon owns its vertices and uvs, and one normal for a flat face). Cutting a paint out
therefore means dropping its `f` lines and compacting the vertex, uv and normal lists, which keeps every other face
exactly as it was (same positions, uvs, normals, order).
"""
from pathlib import Path


def parse(text):
    head, v, vt, vn, blocks = [], [], [], [], []   # blocks: [paint, [faces as ((v, vt, vn) x3)]]
    for line in text.split("\n"):
        if line.startswith("v "):
            v.append(line)
        elif line.startswith("vt "):
            vt.append(line)
        elif line.startswith("vn "):
            vn.append(line)
        elif line.startswith("usemtl "):
            blocks.append([line.split(None, 1)[1].strip(), []])
        elif line.startswith("f "):
            tri = []
            for token in line.split()[1:]:
                a = token.split("/")
                tri.append((int(a[0]), int(a[1]), int(a[2])))
            blocks[-1][1].append(tri)
        elif line.strip() and not blocks and not (v or vt or vn):
            head.append(line)
    return head, v, vt, vn, blocks


def build(head, v, vt, vn, blocks, paints, mtl_name=None, comment=None):
    """ Text of an OBJ with only these paints' faces, vertices compacted. """
    vmap, tmap, nmap = {}, {}, {}
    out_v, out_t, out_n, faces = [], [], [], []
    for paint, tris in blocks:
        if paint not in paints:
            continue
        faces.append(f"usemtl {paint}")
        for tri in tris:
            ids = []
            for a, b, c in tri:
                if a not in vmap:
                    vmap[a] = len(out_v) + 1
                    out_v.append(v[a - 1])
                if b not in tmap:
                    tmap[b] = len(out_t) + 1
                    out_t.append(vt[b - 1])
                if c not in nmap:
                    nmap[c] = len(out_n) + 1
                    out_n.append(vn[c - 1])
                ids.append(f"{vmap[a]}/{tmap[b]}/{nmap[c]}")
            faces.append("f " + " ".join(ids))
    lines = list(head)
    if comment:
        lines.insert(0, comment)
    if mtl_name:
        lines = [l for l in lines if not l.startswith("mtllib")]
        lines.insert(len([l for l in lines if l.startswith("#")]), f"mtllib {mtl_name}")
    return "\n".join(lines + out_v + out_t + out_n + faces) + "\n"


def triangle_count(blocks, paints=None):
    return sum(len(t) for p, t in blocks if paints is None or p in paints)


if __name__ == "__main__":
    import sys
    text = Path(sys.argv[1]).read_text()
    head, v, vt, vn, blocks = parse(text)
    print(head, len(v), len(vt), len(vn), [(p, len(t)) for p, t in blocks])
