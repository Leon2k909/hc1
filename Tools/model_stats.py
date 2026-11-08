#!/usr/bin/env python3
"""Model statistics for before/after comparisons (triangles, vertices, textures).

Run it with `python -I Tools/model_stats.py ...` from the project root.  No third-party
packages are needed.  Every number is measured from files on disk so that different
sessions report the same definitions:

  triangles   = fan-triangulated faces of the OBJ (an n-gon counts n-2); this is what the
                engine draws for that LOD (per instance).
  vertices    = `v` lines of the OBJ (the engine splits them again per UV/normal seam, so
                its own count is higher; use this for comparing like with like).
  texture px  = pixel width x height of each texture file a material references.
  est. GPU    = pixels x 4 bytes x 1.333 (uncompressed RGBA8 with a full mip chain), the
                same worst-case yardstick for every texture; BC7 would be about 1/4 of it.
  compiled    = size on disk of the engine's own compiled `*_c` files (vmdl_c, vtex_c); the
                vtex_c match is best-effort (the engine may pack roughness/metal maps under
                another name, shown as 0), so quote pixels and est. GPU as the main yardsticks.
  Materials whose colour/roughness are plain constants (`[r g b a]`) or engine defaults have
  no texture file and add nothing to the texture totals.

Usage:
  --label NAME            heading for this block (e.g. "BEFORE" / "AFTER")
  --vmdl models/x.vmdl    a model: its LOD OBJs, thresholds, material remaps and vmdl_c size
  --obj path.obj          an OBJ on its own (path relative to the project root or Assets/)
  --vmat materials/x.vmat a material (repeatable); its Texture* files are measured
  --json out.json         also write the numbers as JSON
Paths may be given relative to Assets/ (e.g. models/props/x.vmdl) or as absolute paths.
"""
import argparse, glob, json, os, re, struct, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS = os.path.join(ROOT, "Assets")
MIP = 1.3333


def resolve(p):
    if os.path.isabs(p) and os.path.exists(p):
        return p
    for base in (ASSETS, ROOT, os.getcwd()):
        q = os.path.join(base, p)
        if os.path.exists(q):
            return q
    return None


def obj_stats(path):
    nv = nt = 0
    mn = [1e18] * 3
    mx = [-1e18] * 3
    mats = []
    with open(path, "r", errors="ignore") as fh:
        for line in fh:
            if line.startswith("v "):
                nv += 1
                a = line.split()
                for i in range(3):
                    v = float(a[i + 1])
                    mn[i] = min(mn[i], v)
                    mx[i] = max(mx[i], v)
            elif line.startswith("f "):
                nt += max(0, len(line.split()) - 3)
            elif line.startswith("usemtl "):
                m = line.split(None, 1)[1].strip()
                if m not in mats:
                    mats.append(m)
    ext = [round(mx[i] - mn[i], 2) for i in range(3)] if nv else [0, 0, 0]
    return {"triangles": nt, "vertices": nv, "materials": mats, "extent_in": ext,
            "extent_m": [round(e * 0.0254, 3) for e in ext], "bytes": os.path.getsize(path)}


def image_size(path):
    try:
        with open(path, "rb") as f:
            h = f.read(32)
            ext = os.path.splitext(path)[1].lower()
            if h[:8] == b"\x89PNG\r\n\x1a\n":
                return struct.unpack(">II", h[16:24])
            if ext == ".tga":
                return struct.unpack("<HH", h[12:16])
            if h[:2] == b"\xff\xd8":
                f.seek(2)
                while True:
                    b = f.read(1)
                    while b and b != b"\xff":
                        b = f.read(1)
                    m = f.read(1)
                    if not m:
                        return None
                    if m[0] in (0xC0, 0xC1, 0xC2):
                        f.read(3)
                        hh, ww = struct.unpack(">HH", f.read(4))
                        return (ww, hh)
                    n = struct.unpack(">H", f.read(2))[0]
                    f.seek(n - 2, 1)
    except Exception:
        return None
    return None


def vmat_textures(vmat_path):
    out = []
    with open(vmat_path, "r", errors="ignore") as fh:
        for line in fh:
            m = re.match(r'\s*(Texture\w+|g_t\w+)\s+"([^"]+)"', line)
            if m:
                out.append((m.group(1), m.group(2)))
    return out


def compiled_for(tex_abs):
    d, n = os.path.split(tex_abs)
    stem = os.path.splitext(n)[0]
    return sum(os.path.getsize(p) for p in glob.glob(os.path.join(d, glob.escape(stem) + "_*.vtex_c")))


def vmdl_info(path):
    txt = open(path, "r", errors="ignore").read()
    meshes = re.findall(r'name\s*=\s*"([^"]+)"\s*filename\s*=\s*"([^"]+)"', txt)
    thresholds = re.findall(r'switch_threshold\s*=\s*([\d.]+)\s*meshes\s*=\s*\["([^"]+)"\]', txt)
    remaps = re.findall(r'from\s*=\s*"([^"]+)"\s*to\s*=\s*"([^"]+)"', txt)
    return meshes, thresholds, remaps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="MODEL")
    ap.add_argument("--vmdl", action="append", default=[])
    ap.add_argument("--obj", action="append", default=[])
    ap.add_argument("--vmat", action="append", default=[])
    ap.add_argument("--json")
    a = ap.parse_args()

    res = {"label": a.label, "objs": [], "textures": [], "vmdl": []}
    objs = list(a.obj)
    vmats = list(a.vmat)
    for v in a.vmdl:
        vp = resolve(v)
        if not vp:
            print("missing vmdl:", v)
            continue
        meshes, thr, remaps = vmdl_info(vp)
        thr_map = {m: t for t, m in thr}
        c = vp + "_c"
        res["vmdl"].append({"path": v, "vmdl_c_bytes": os.path.getsize(c) if os.path.exists(c) else None,
                            "lods": [(n, f, thr_map.get(n)) for n, f in meshes]})
        for n, f in meshes:
            objs.append(f)
        for _from, to in remaps:
            if to.endswith(".vmat"):
                vmats.append(to)

    print(f"==== {a.label} ====")
    for v in res["vmdl"]:
        print(f"vmdl {v['path']}  compiled vmdl_c: {v['vmdl_c_bytes']} bytes")
    for o in dict.fromkeys(objs):
        op = resolve(o)
        if not op:
            print("missing obj:", o)
            continue
        s = obj_stats(op)
        s["path"] = o
        res["objs"].append(s)
        print(f"OBJ {o}\n    triangles {s['triangles']:,}  vertices {s['vertices']:,}  materials {len(s['materials'])}"
              f"  extent {s['extent_in']} in ({s['extent_m']} m)  file {s['bytes']:,} bytes")

    seen = set()
    tot_px = tot_gpu = tot_comp = 0
    for m in dict.fromkeys(vmats):
        mp = resolve(m)
        if not mp:
            print("missing vmat:", m)
            continue
        for slot, tp in vmat_textures(mp):
            if tp.startswith("[") or tp.startswith("materials/default/"):
                continue  # a constant colour/value or an engine default: no texture file of its own
            ta = resolve(tp)
            if not ta:
                res["textures"].append({"vmat": m, "slot": slot, "path": tp, "note": "not found under Assets (engine/mounted)"})
                continue
            if ta in seen:
                continue
            seen.add(ta)
            wh = image_size(ta)
            px = wh[0] * wh[1] if wh else 0
            gpu = int(px * 4 * MIP)
            comp = compiled_for(ta)
            tot_px += px
            tot_gpu += gpu
            tot_comp += comp
            res["textures"].append({"vmat": m, "slot": slot, "path": tp, "w": wh[0] if wh else None,
                                    "h": wh[1] if wh else None, "file_bytes": os.path.getsize(ta),
                                    "est_gpu_bytes": gpu, "compiled_bytes": comp})
    print(f"MATERIALS {len(set(vmats))}  unique texture files {len(seen)}")
    for t in res["textures"]:
        if "w" in t:
            print(f"    {t['slot']:<22} {t['w']}x{t['h']}  file {t['file_bytes']:,} B  est.GPU {t['est_gpu_bytes']/1048576:.2f} MB"
                  f"  compiled {t['compiled_bytes']:,} B  {t['path']}")
        else:
            print(f"    {t['slot']:<22} ({t['note']}) {t['path']}")
    res["totals"] = {"unique_textures": len(seen), "texture_pixels": tot_px, "est_gpu_bytes": tot_gpu,
                     "compiled_vtex_bytes": tot_comp}
    print(f"TOTAL texture pixels {tot_px:,} ({tot_px/1e6:.2f} MP)  est.GPU {tot_gpu/1048576:.2f} MB  compiled vtex_c {tot_comp:,} B")
    if a.json:
        json.dump(res, open(a.json, "w"), indent=1)


if __name__ == "__main__":
    main()
