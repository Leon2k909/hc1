"""Thin overlapping slate courses on Lowtide's four low shed roofs.

The generated albedo is retained. Course boundaries are measured from that
image, then used as both geometry edges and UV boundaries. Original roof planes
remain as substrate; this module adds visual geometry with no collision.
"""
import argparse
import hashlib
import json
import math
import re

import numpy as np
from PIL import Image

import map_kit as K
import lowtide_roofs as R

REPORT = K.ROOT / "output/lowtide/quality-pass"
MARKER = "# Lowtide shed slate relief v1"
TEXTURE_SCALE = 1.2192
SPAN = 96 / TEXTURE_SCALE  # 2 metres in engine inches.
V_BIAS = (TEXTURE_SCALE - 1) / TEXTURE_SCALE


def image_courses():
    """Find the eleven photographed overlap lines; do not modify any pixels."""
    image = np.asarray(Image.open(R.SOURCE).convert("RGB"), float)
    luminance = image @ np.array((.2126, .7152, .0722))
    profile = np.median(luminance, axis=1)
    rows = [0]
    for i in range(1, 12):
        centre = len(profile) * i / 12
        lo, hi = round(centre - 12), round(centre + 12)
        rows.append(lo + int(np.argmin(profile[lo:hi])))
    rows.append(len(profile))
    # OBJ's V increases up the image. Include the repeat boundary explicitly.
    return np.array([1 - y / len(profile) for y in reversed(rows)])


def panel(m, L, bounds, eaves, pitch, sign, side, phases, report):
    e0, e1, n0, n1 = bounds
    scale = math.sqrt(1 + pitch * pitch)
    run = (n1 - n0) * .5 * scale
    normal = np.array((0, sign * pitch, 1)) / scale
    uphill = np.array((0, -sign, pitch)) / scale
    origin = np.array((side * e0, n1 if sign > 0 else n0, eaves))
    along = np.array((side, 0, 0))
    seed = L.keyed(e0, eaves, side, sign, "slate relief")
    phase = float(phases[seed % 12])
    u_phase = (seed // 12 % 8) / 8
    cut = [(0., phase)]
    for cycle in range(math.ceil(phase + run / SPAN) + 1):
        for v in phases[:-1] + cycle:
            d = (v - phase) * SPAN
            if .001 < d < run - .001:
                cut.append((float(d), float(v)))
    cut.append((run, phase + run / SPAN))
    cut.sort()
    count = 0
    for row, ((low, vl), (high, vh)) in enumerate(zip(cut, cut[1:])):
        # The photograph supplies fine joints. One planar ribbon per course
        # avoids spending triangles on invisible coplanar tile subdivisions.
        cuts = [0.,e1-e0]
        # Keep each face planar. Twisted quads at this small physical depth
        # produce shadow acne when imported with one normal for both triangles.
        tips = [.245 + .025 * math.sin(seed % 71 + row * 2.4)] * len(cuts)
        for i, (a, b) in enumerate(zip(cuts, cuts[1:])):
            # 1.5 mm at the concealed head, approximately 6 mm at the lap.
            # A small transverse variation breaks a perfectly straight edge.
            bottom = [origin+along*x+uphill*low+normal*h for x,h in ((a,tips[i]),(b,tips[i+1]))]
            top = [origin+along*x+uphill*high+normal*.06 for x in (a,b)]
            ua, ub = (u_phase+a/SPAN)/TEXTURE_SCALE, (u_phase+b/SPAN)/TEXTURE_SCALE
            # The model importer flips OBJ V before the shader multiplies by
            # its material scale. Compensate that order so the geometric lap
            # lands on the photographed lap, not through the middle of a slate.
            v0, v1 = vl/TEXTURE_SCALE+V_BIAS, vh/TEXTURE_SCALE+V_BIAS
            L.card(m,"slate",[bottom[0],bottom[1],top[1],top[0]],normal,
                   uv=[(ua,v0),(ub,v0),(ub,v1),(ua,v1)])
            foot = [origin+along*x+uphill*low+normal*.045 for x in (a,b)]
            # The overlap's exposed cut edge has real depth, including in the
            # shadow pass. Its narrow UV slice samples the dark photographed lap.
            L.card(m,"slate",[foot[0],foot[1],bottom[1],bottom[0]],-uphill,
                   uv=[(ua,v0+.0005),(ub,v0+.0005),(ub,v0),(ua,v0)])
            # A six-millimetre cut edge becomes subpixel at player distance.
            # Use the parent roof's shading normal for that thin edge; the
            # filtered photograph already supplies its dark cleft. An abrupt
            # downward normal here creates unfiltered black moire lines.
            m.polygon_normals[("slate",len(m.polygons["slate"])-1)] = [normal] * 4
            count += 4
        # Close the two verges against the retained substrate.
        for x, tip, outward in ((0.,tips[0],-along),(e1-e0,tips[-1],along)):
            points=[origin+along*x+uphill*low,
                    origin+along*x+uphill*high,
                    origin+along*x+uphill*high+normal*.06,
                    origin+along*x+uphill*low+normal*tip]
            u=(u_phase+x/SPAN)/TEXTURE_SCALE
            L.card(m,"slate",points,outward,uv=[(u,v0),(u,v1),(u+.0005,v1),(u+.0005,v0)])
            count += 2
    if report is not None:
        report.append(dict(bounds=bounds,side=side,slope=sign,eaves=eaves,
                           pitch=pitch,courseCount=len(cut)-1,triangles=count,
                           lowerLapInches=[.22,.27],headInches=.06))


def build(L, report=None):
    model=K.Model()
    phases=image_courses()
    assert len(phases)==13 and np.all(np.diff(phases) > .06)
    for side in (-1,1):
        for bounds,eaves in ((L.QUAY_SHED,276.),(L.YARD_SHED,236.)):
            # Ask the block generator for its actual roof slope rather than
            # assuming roof()'s default: block() deliberately uses 0.75.
            probe=K.Model()
            L.block(probe,*bounds,eaves-40,{},L.EAST,roof_along="e")
            roof_normal=probe.polygons["slate"][0][1]
            pitch=abs(float(roof_normal[1]/roof_normal[2]))
            for sign in (-1,1):
                panel(model,L,bounds,eaves,pitch,sign,side,phases,report)
    L.configure(model)
    assert not model.boxes and not model.hulls and not model.props
    return model


def stage(revise=False):
    import lowtide_map as L
    stage=REPORT/"roof-relief-stage"
    before=REPORT/"roof-relief-before"
    stage.mkdir(parents=True,exist_ok=True)
    before.mkdir(parents=True,exist_ok=True)
    if revise:
        previous=json.loads((REPORT/"roof-relief-manifest.json").read_text())
        for name,change in previous["changes"].items():
            assert hashlib.sha256((K.ROOT/name).read_bytes()).hexdigest()==change["after"],"Roof source changed since previous import"
    panels=[]
    model=build(L,panels)
    extra_obj=stage/"roof-relief-addition.obj"
    count=K.write_obj(extra_obj,model,"lowtide_finish")
    folder=K.ASSETS/"models/maps/lowtide"
    source=before if revise else folder
    original=(source/"lowtide_finish.obj").read_text().splitlines()
    assert MARKER not in original,"Relief already installed; do not append twice"
    counts={p:sum(s.startswith(p+" ") for s in original) for p in ("v","vt","vn")}
    extra=[]
    for line in extra_obj.read_text().splitlines():
        if line.startswith(("v ","vt ","vn ","usemtl ")): extra.append(line)
        elif line.startswith("f "):
            refs=["/".join(str(int(value)+counts[p]) for value,p in zip(v.split("/"),("v","vt","vn"))) for v in line.split()[1:]]
            extra.append("f "+" ".join(refs))
    attrs=[s for p in ("v ","vt ","vn ") for s in original+extra if s.startswith(p)]
    headers=[s for s in original if not s.startswith(("v ","vt ","vn ","usemtl ","f "))]
    draws=[s for s in original+extra if s.startswith(("usemtl ","f "))]
    (stage/"lowtide_finish.obj").write_text("\n".join(headers+[MARKER]+attrs+draws)+"\n")
    old_resource=(source/"lowtide_finish.vmdl").read_text()
    anchor=re.search(r'[^\n]*\{ from = "lt_drain_iron\.vmat"[^\n]*\n',old_resource)
    assert anchor
    remap=f'\t\t\t\t\t\t\t{{ from = "slate.vmat" to = "{R.MATERIAL}" }},\n'
    assert 'from = "slate.vmat"' not in old_resource
    (stage/"lowtide_finish.vmdl").write_text(old_resource[:anchor.end()]+remap+old_resource[anchor.end():])
    mtl=(source/"lowtide_finish.mtl").read_text()
    assert "newmtl slate\n" not in mtl
    (stage/"lowtide_finish.mtl").write_text(mtl+"newmtl slate\nKd 1 1 1\nd 1\n")
    def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
    changes={}
    for ext in ("obj","mtl","vmdl"):
        path=folder/f"lowtide_finish.{ext}"
        backup=before/path.name
        if backup.exists() and not revise: assert backup.read_bytes()==path.read_bytes(),"Source changed since staging"
        elif backup.exists(): pass
        else: backup.write_bytes(path.read_bytes())
        changes[path.relative_to(K.ROOT).as_posix()]={"before":sha(path),"after":sha(stage/path.name)}
    protected=[L.SCENE_FILE,R.SOURCE]+list(R.DIRECTORY.glob("*.png"))+[K.ASSETS/R.MATERIAL]
    protected += [p for p in folder.iterdir() if p.suffix in (".obj",".vmdl")]
    info=dict(addedTriangles=count,panels=panels,textureCourseBoundaries=image_courses().tolist(),
              baselineBefore={p.relative_to(before).as_posix():sha(p) for p in before.iterdir()},
              collisionAdded=False,changes=changes,newMaterialRemap=remap,
              protectedBefore={p.relative_to(K.ROOT).as_posix():sha(p) for p in protected})
    (REPORT/"roof-relief-manifest.json").write_text(json.dumps(info,indent=2)+"\n")
    print(json.dumps(dict(addedTriangles=count,panels=len(panels),courses=sum(p["courseCount"] for p in panels),
                         collisionAdded=False,texturePixelsChanged=False),indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage",action="store_true")
    parser.add_argument("--revise",action="store_true",help="Replace only this pass, retaining the original snapshot")
    args=parser.parse_args()
    if args.stage: stage(args.revise)
