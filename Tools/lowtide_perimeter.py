"""Close Lowtide's exposed background building shells without rebuilding the map.

Geometry is appended to Harbour Details. Existing architecture, collision,
scene objects and lighting resources are retained. Run --stage, then install
the staged three files through the editor.
"""
import argparse
import copy
import hashlib
import json
import math
import re
from pathlib import Path

import numpy as np
import map_kit as K

REPORT = K.ROOT / "output/lowtide/quality-pass"
MARKER = "# Lowtide perimeter building closures v1"


def layout(L):
    """Read the actual block calls and north-row roofs, with no asset writes."""
    blocks, roofs = [], []
    originals = (L.block, L.roof, L.speicher)
    def block(m,e0,e1,n0,n1,eaves,faces,style,z0=0,roof_along="n"):
        blocks.append(dict(bounds=(e0,e1,n0,n1),eaves=eaves,z0=z0,
                           faces=copy.deepcopy(faces),roof_along=roof_along))
        return eaves+40
    def roof(m,e0,e1,n0,n1,z0,along="n",pitch=.8,paint="slate",ridge="copper",ends=True):
        roofs.append(dict(bounds=(e0,e1,n0,n1),height=z0,along=along))
        return z0+((e1-e0) if along=="n" else (n1-n0))*pitch*.5
    try:
        L.block, L.roof, L.speicher = block, roof, lambda *a,**k: None
        L.half()
    finally:
        L.block, L.roof, L.speicher = originals
    assert len(blocks)==6 and len(roofs)==3, "Review changed perimeter layout before rebuilding closures"
    return blocks, roofs


def runs_for(block,T):
    e0,e1,n0,n1 = block["bounds"]
    faces = block["faces"]
    ends = any(f in faces for f in ("+n","-n"))
    return {face:tuple(kw.get("run",(e0,e1) if face[-1]=="n" else
                 (n0+T,n1-T) if ends else (n0,n1))) for face,kw in faces.items()}


def missing_walls(L, block):
    e0,e1,n0,n1 = block["bounds"]
    runs = runs_for(block,L.T)
    for face in ("-n","+n","-e","+e"):
        a,b = (e0,e1) if face[-1]=="n" else (n0,n1)
        # Existing perpendicular facade ends already occupy the corner thickness.
        if face[-1]=="n":
            edge = n0 if face[0]=="-" else n1
            for adjacent,low in (("-e",True),("+e",False)):
                if adjacent in runs and runs[adjacent][0] <= edge <= runs[adjacent][1]:
                    if low: a += L.T
                    else: b -= L.T
        else:
            edge = e0 if face[0]=="-" else e1
            for adjacent,low in (("-n",True),("+n",False)):
                if adjacent in runs and runs[adjacent][0] <= edge <= runs[adjacent][1]:
                    if low: a += L.T
                    else: b -= L.T
        spans = [(a,b)] if face not in runs else [(a,min(b,runs[face][0])),(max(a,runs[face][1]),b)]
        for lo,hi in spans:
            if hi-lo < .01: continue
            across = (n0,n0+L.T) if face=="-n" else (n1-L.T,n1) if face=="+n" else (e0,e0+L.T) if face=="-e" else (e1-L.T,e1)
            yield K.Wall("e" if face[-1]=="n" else "n",(lo,hi),across,(block["z0"],block["eaves"]+40),face)


def plain_wall(m,L,wall):
    d,_,out = L.wall_out(wall)
    a,b = wall.run
    z0,z1 = wall.z
    L.card(m,"brick",[wall.point(a,d,z0),wall.point(b,d,z0),wall.point(b,d,z1),wall.point(a,d,z1)],out)


def quay_end(m,L,wall,eaves):
    """A complete five-storey warehouse end, tied into the existing front."""
    old = (L.courses,L.cornice,L.window)
    windows=[]
    def window(model,w,o,style,pane=None,glass=None):
        old[2](model,w,o,style,pane,glass)
        windows.append((w,o))
    try:
        L.courses = lambda *a,**k: None
        L.cornice = lambda *a,**k: None
        L.window = window
        L.facade(m,wall,L.EAST,eaves,[2295,2450,2605],levels=L.BLOCK_LEVELS,
                 pilaster_every=1,end=False)
    finally:
        L.courses,L.cornice,L.window=old
    for w,o in windows:
        L.MASONRY.sill(m,L,w,o)
        if o.z0 < 200: L.MASONRY.arch(m,L,w,o)
    a,b = wall.run
    # Stop mouldings at the existing front's corner; do not overlap its caps.
    for z in L.BLOCK_LEVELS:
        L.slab(m,wall,a,b,0,2,z-11,z-2,L.EAST.band)
    L.slab(m,wall,a,b,0,2.5,0,44,L.EAST.stone)
    for r in np.arange(a+10,b-6,16):
        L.slab(m,wall,r-3,r+3,0,5,eaves-36,eaves-22,L.EAST.band)
    L.slab(m,wall,a,b,0,7,eaves-22,eaves-12,L.EAST.band)
    L.slab(m,wall,a+2.02,b,-L.T-2,4,eaves+40,eaves+46,L.EAST.stone)
    # A modest cast-iron loft vent breaks up the previously empty triangular end.
    d,sign,out = L.wall_out(wall)
    centre = wall.point(2450,d+sign*1.6,eaves+112)
    along = np.array((1,0,0),float)
    up = np.array((0,0,1),float)
    L.card(m,"lt_drain_iron",[centre+24*(math.cos(t)*along+math.sin(t)*up)
           for t in np.linspace(0,2*math.pi,33)[:-1]],out)
    L.torus(m,centre+out*.8,along,up,25.7,2.2,"lt_brick_glazed",segments=32,sides=6)
    for z in range(-18,19,6):
        half=math.sqrt(23*23-z*z)
        L.bar(m,centre+up*z-along*half+out*2,centre+up*z+along*half+out*2,.8,"lt_drain_edge",sides=6)


def anchored_uvs(model,name):
    shift = K.uv_offset(name)
    for paint in ("brick","lt_brick_soot","lt_brick_glazed","ashlar_grey"):
        for i,(points,normal) in enumerate(model.polygons.get(paint,[])):
            if (paint,i) in model.polygon_uvs: continue
            model.polygon_uvs[paint,i] = [K.face_uv(K.to_world(p),K.to_world(normal),paint,shift,
                                         model.tile_overrides.get(paint)) for p in points]


def build(L,report=None):
    blocks, roofs = layout(L)
    east=K.Model()
    walls=[]
    for block in blocks:
        for wall in missing_walls(L,block):
            hero = block["bounds"]==(2200.0,2700.0,-1050.0,600.0) and wall.outward=="-n"
            if hero: quay_end(east,L,wall,block["eaves"])
            else: plain_wall(east,L,wall)
            walls.append(dict(bounds=block["bounds"],face=wall.outward,run=wall.run,z=wall.z,detailed=hero))
    # The northern row has roofs and street fronts, but lacked side/back walls.
    for roof in roofs:
        e0,e1,n0,n1=roof["bounds"]
        for face,run,across in (("+n",(e0,e1),(n1-L.T,n1)),
                               ("-e",(n0+L.T,n1),(e0,e0+L.T)),
                               ("+e",(n0+L.T,n1),(e1-L.T,e1))):
            if face=="-e" and e0==L.FLEET: continue # Existing canal facade.
            wall=K.Wall("e" if face[-1]=="n" else "n",run,across,(0,roof["height"]),face)
            plain_wall(east,L,wall)
            walls.append(dict(bounds=roof["bounds"],face=face,run=run,z=wall.z,detailed=False))
    west=east.mirrored(L.WEST_PAINTS)
    for name,model in (("lowtide_east",east),("lowtide_west",west)):
        L.configure(model)
        L.WINDOWS.configure(model)
        anchored_uvs(model,name)
    result=K.Model().extend(east).extend(west)
    assert not result.boxes and not result.hulls and not result.props
    if report is not None:
        report.update(eastWalls=walls,mirroredWest=True,collisionAdded=False,
                      detailedEnds=2,sealedWindows=len(result.polygons.get("rw_window_dark",[])))
    return result


def stage():
    import lowtide_map as L
    stage=REPORT/"perimeter-stage"
    before=REPORT/"perimeter-before"
    stage.mkdir(parents=True,exist_ok=True)
    before.mkdir(parents=True,exist_ok=True)
    info={}
    addition=build(L,info)
    extra_obj=stage/"perimeter-addition.obj"
    info["addedTriangles"]=K.write_obj(extra_obj,addition,"lowtide_finish")
    folder=K.ASSETS/"models/maps/lowtide"
    old_obj=(folder/"lowtide_finish.obj").read_text()
    assert MARKER not in old_obj,"Perimeter already installed; do not append twice"
    original=old_obj.splitlines()
    counts={p:sum(s.startswith(p+" ") for s in original) for p in ("v","vt","vn")}
    extra=[]
    for line in extra_obj.read_text().splitlines():
        if line.startswith(("v ","vt ","vn ","usemtl ")): extra.append(line)
        elif line.startswith("f "):
            refs=["/".join(str(int(value)+counts[p]) for value,p in zip(v.split("/"),("v","vt","vn"))) for v in line.split()[1:]]
            extra.append("f "+" ".join(refs))
    attrs=[line for prefix in ("v ","vt ","vn ") for line in original+extra if line.startswith(prefix)]
    headers=[s for s in original if not s.startswith(("v ","vt ","vn ","usemtl ","f "))]
    draws=[s for s in original+extra if s.startswith(("usemtl ","f "))]
    (stage/"lowtide_finish.obj").write_text("\n".join(headers+[MARKER]+attrs+draws)+"\n")
    old_model=(folder/"lowtide_finish.vmdl").read_text()
    marker=re.search(r'[^\n]*\{ from = "lt_drain_iron\.vmat"[^\n]*\n',old_model)
    assert marker
    remaps=[]
    for paint in sorted(addition.polygons):
        if f'from = "{paint}.vmat"' in old_model: continue
        path=addition.material_overrides.get(paint)
        assert path and (K.ASSETS/path).exists(),(paint,path)
        remaps.append(f'\t\t\t\t\t\t\t{{ from = "{paint}.vmat" to = "{path}" }},')
    updated_model=old_model[:marker.end()]+"\n".join(remaps)+"\n"+old_model[marker.end():]
    (stage/"lowtide_finish.vmdl").write_text(updated_model)
    mtl=(folder/"lowtide_finish.mtl").read_text()
    for paint in sorted(addition.polygons):
        if f"newmtl {paint}\n" not in mtl: mtl+=f"newmtl {paint}\nKd 1 1 1\nd 1\n"
    (stage/"lowtide_finish.mtl").write_text(mtl)
    def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
    changes={}
    for extension in ("obj","mtl","vmdl"):
        source=folder/f"lowtide_finish.{extension}"
        backup=before/source.name
        if backup.exists(): assert backup.read_bytes()==source.read_bytes(),"Source changed since staging"
        else: backup.write_bytes(source.read_bytes())
        changes[str(source.relative_to(K.ROOT)).replace("\\","/")]={"before":sha(source),"after":sha(stage/source.name)}
    protected=[L.SCENE_FILE]+[p for p in folder.iterdir() if p.suffix in (".obj",".vmdl")]
    info.update(changes=changes,protectedBefore={str(p.relative_to(K.ROOT)).replace("\\","/"):sha(p) for p in protected},newMaterialRemaps=remaps)
    (REPORT/"perimeter-manifest.json").write_text(json.dumps(info,indent=2)+"\n")
    print(json.dumps({k:v for k,v in info.items() if k not in ("protectedBefore","eastWalls")},indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage",action="store_true")
    if parser.parse_args().stage: stage()
