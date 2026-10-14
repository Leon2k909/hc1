"""Construction detail for Lowtide's low sheds: louvred vents and formed ridges.

Additive, collision-free geometry. Stage outside Assets, inspect, then import
through the editor. Existing slate surfaces and all authored geometry remain.
"""
import argparse
import hashlib
import json
import math
import re

import numpy as np
import map_kit as K

REPORT=K.ROOT/"output/lowtide/quality-pass"
MARKER="# Lowtide shed gable and ridge details v1"


def vent(m,L,centre,out,radius,paint,seed):
    c=np.asarray(centre,float)
    out=np.asarray(out,float)
    across=np.array((0,1,0),float)
    up=np.array((0,0,1),float)
    def p(angle,r,depth):
        return c+across*math.cos(angle)*r+up*math.sin(angle)*r+out*depth
    # A sealed dark backing sits behind the cast frame and the angled blades.
    L.card(m,"lt_hull_black",[p(t,radius+.4,.12) for t in np.linspace(0,2*math.pi,49)[:-1]],out)
    L.torus(m,c+out*1.05,across,up,radius+.5,.75,paint,segments=48,sides=8)
    # Individual radial clay voussoirs with chamfered front edges.
    count=round(2*math.pi*(radius+4)/4)
    for i in range(count):
        a=2*math.pi*i/count+.006
        b=2*math.pi*(i+1)/count-.006
        proud=1.65+.10*math.sin(i*2.23+seed%17)
        base=[p(a,radius+1.4,.14),p(b,radius+1.4,.14),p(b,radius+7.0,.14),p(a,radius+7.0,.14)]
        edge=[p(a,radius+1.4,proud-.28),p(b,radius+1.4,proud-.28),p(b,radius+7.0,proud-.28),p(a,radius+7.0,proud-.28)]
        front=[p(a+.004,radius+1.68,proud),p(b-.004,radius+1.68,proud),
               p(b-.004,radius+6.72,proud),p(a+.004,radius+6.72,proud)]
        u=.098+((seed+i*7)%5)/6
        uv=[(u,.992),(u,.966),(u+.14,.966),(u+.14,.992)]
        L.card(m,"lt_arch_clay",front,out,uv=uv)
        centre_brick=np.mean(base+front,axis=0)
        for j in range(4):
            k=(j+1)%4
            for points in ([base[j],base[k],edge[k],edge[j]],[edge[j],edge[k],front[k],front[j]]):
                L.card(m,"lt_arch_clay",points,np.mean(points,axis=0)-centre_brick,uv=uv)
    blades=0
    for z in np.arange(-radius+3,radius-2,5.2):
        half=math.sqrt(max(0,(radius-.55)**2-(abs(z)+2.0)**2))
        if half<2:continue
        # Rain-shedding face, with a folded lower lip and closed cut ends.
        high=c+up*(z+1.9)+out*.65
        low=c+up*(z-1.9)+out*3.15
        points=[high-across*half,high+across*half,low+across*half,low-across*half]
        L.card(m,paint,points,out+up*.4)
        lip=low-up*.42
        L.card(m,paint,[low-across*half,low+across*half,lip+across*half,lip-across*half],out)
        for sign in (-1,1):
            L.card(m,paint,[high+across*half*sign,low+across*half*sign,lip+across*half*sign],across*sign)
        blades+=1
    for x in (-radius*.42,radius*.42):
        half=math.sqrt(radius*radius-x*x)
        L.bar(m,c+across*x-up*half+out*.4,c+across*x+up*half+out*.4,.42,"lt_drain_iron",sides=6)
    return dict(centre=list(centre),normal=list(out),radius=radius,radialBricks=count,blades=blades)


def ridge(m,L,bounds,eaves,side):
    e0,e1,n0,n1=bounds
    nc=(n0+n1)/2
    z=eaves+(n1-n0)*.5*.75
    # This formed cap encloses the original eight-inch square ridge. The wings
    # meet the slate; the rounded crown and lapped joints replace its box outline.
    profile=[(-11.,-8.1)]+[(6*math.cos(t),6*math.sin(t)) for t in np.linspace(math.pi,0,17)]+[(11.,-8.1)]
    def p(e,q,lift=0):return np.array((side*e,nc+q[0],z+q[1]+lift))
    def sheet(a,b,lift=0):
        for q0,q1 in zip(profile,profile[1:]):
            pts=[p(a,q0,lift),p(b,q0,lift),p(b,q1,lift),p(a,q1,lift)]
            mid=(np.array(q0)+q1)/2
            L.card(m,"lt_drain_edge",pts,(0,mid[0],max(1,mid[1]+3)))
    sheet(e0-.5,e1+.5)
    for e,direction in ((e0-.5,-side),(e1+.5,side)):
        bottom=p(e,(0,-8.1))
        for a,b in zip(profile,profile[1:]):
            L.card(m,"lt_drain_iron",[bottom,p(e,a),p(e,b)],(direction,0,0))
    seams=0
    for e in np.arange(e0+48,e1,48):
        sheet(e-.36,e+.36,.32)
        seams+=1
    return dict(bounds=bounds,side=side,height=z,seams=seams)


def build(L,info=None):
    m=K.Model()
    vents=[];ridges=[]
    for side in (-1,1):
        paint="lt_frame_green" if side>0 else "lt_frame_cream"
        for bounds,eaves,radius in ((L.QUAY_SHED,276.,28.),(L.YARD_SHED,236.,17.)):
            e0,e1,n0,n1=bounds
            z=eaves+(n1-n0)*.5*.75*.42
            for e,direction in ((e0,-side),(e1,side)):
                vents.append(vent(m,L,(side*e,(n0+n1)/2,z),(direction,0,0),radius,paint,L.keyed(e,side,"shed vent")))
            ridges.append(ridge(m,L,bounds,eaves,side))
    L.configure(m)
    assert not m.boxes and not m.hulls and not m.props
    if info is not None:info.update(vents=vents,ridges=ridges,collisionAdded=False)
    return m


def stage():
    import lowtide_map as L
    stage=REPORT/"shed-details-stage";before=REPORT/"shed-details-before"
    stage.mkdir(parents=True,exist_ok=True);before.mkdir(parents=True,exist_ok=True)
    info={};model=build(L,info)
    addition=stage/"shed-details-addition.obj"
    info["addedTriangles"]=K.write_obj(addition,model,"lowtide_finish")
    folder=K.ASSETS/"models/maps/lowtide"
    original=(folder/"lowtide_finish.obj").read_text().splitlines()
    assert MARKER not in original,"Details already installed"
    counts={p:sum(s.startswith(p+" ") for s in original) for p in ("v","vt","vn")}
    extra=[]
    for line in addition.read_text().splitlines():
        if line.startswith(("v ","vt ","vn ","usemtl ")):extra.append(line)
        elif line.startswith("f "):
            refs=["/".join(str(int(value)+counts[p]) for value,p in zip(v.split("/"),("v","vt","vn"))) for v in line.split()[1:]]
            extra.append("f "+" ".join(refs))
    attrs=[s for p in ("v ","vt ","vn ") for s in original+extra if s.startswith(p)]
    headers=[s for s in original if not s.startswith(("v ","vt ","vn ","usemtl ","f "))]
    draws=[s for s in original+extra if s.startswith(("usemtl ","f "))]
    (stage/"lowtide_finish.obj").write_text("\n".join(headers+[MARKER]+attrs+draws)+"\n")
    old=(folder/"lowtide_finish.vmdl").read_text()
    anchor=re.search(r'[^\n]*\{ from = "lt_drain_iron\.vmat"[^\n]*\n',old);assert anchor
    remaps=[]
    for paint in sorted(model.polygons):
        if f'from = "{paint}.vmat"' not in old:
            path=model.material_overrides[paint];assert (K.ASSETS/path).exists()
            remaps.append(f'\t\t\t\t\t\t\t{{ from = "{paint}.vmat" to = "{path}" }},')
    (stage/"lowtide_finish.vmdl").write_text(old[:anchor.end()]+"\n".join(remaps)+"\n"+old[anchor.end():])
    mtl=(folder/"lowtide_finish.mtl").read_text()
    for paint in sorted(model.polygons):
        if f"newmtl {paint}\n" not in mtl:mtl+=f"newmtl {paint}\nKd 1 1 1\nd 1\n"
    (stage/"lowtide_finish.mtl").write_text(mtl)
    def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
    changes={}
    for ext in ("obj","mtl","vmdl"):
        path=folder/f"lowtide_finish.{ext}";backup=before/path.name
        if backup.exists():assert backup.read_bytes()==path.read_bytes(),"Source changed since staging"
        else:backup.write_bytes(path.read_bytes())
        changes[path.relative_to(K.ROOT).as_posix()]={"before":sha(path),"after":sha(stage/path.name)}
    protected=[L.SCENE_FILE]+[p for p in folder.iterdir() if p.suffix in (".obj",".vmdl")]
    protected += [K.ASSETS/p for p in set(model.material_overrides.values())]
    info.update(changes=changes,newMaterialRemaps=remaps,
                protectedBefore={p.relative_to(K.ROOT).as_posix():sha(p) for p in protected})
    (REPORT/"shed-details-manifest.json").write_text(json.dumps(info,indent=2)+"\n")
    print(json.dumps(dict(addedTriangles=info["addedTriangles"],vents=len(info["vents"]),ridges=len(info["ridges"]),collisionAdded=False),indent=2))


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument("--stage",action="store_true")
    if parser.parse_args().stage:stage()
