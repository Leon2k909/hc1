"""Stage museum construction details and corrected dressing/hedge meshes.

All new geometry is visual only. Existing collider resources and gameplay objects
are retained by the native importer. Model sources are never published directly.
"""
from pathlib import Path
import hashlib
import inspect
import json
import math
import os
import platform
platform.machine=lambda:os.environ.get("PROCESSOR_ARCHITECTURE","AMD64")
import numpy as np
import map_kit as K
import cerroblanco_map as C
import cerroblanco_parts as P

ROOT=Path(__file__).resolve().parent.parent
STAGE=ROOT/"output/cerroblanco/stage"
RESOURCE="models/maps/cerroblanco/quality-v1"
MATERIAL="materials/cerroblanco/quality-v1"
HEDGE_STAGE=ROOT/"output/cerroblanco/hedge-fix"


def recorder(module,name,records):
    original=getattr(module,name)
    signature=inspect.signature(original)
    def call(*args,**kwargs):
        bound=signature.bind(*args,**kwargs)
        bound.apply_defaults()
        records.append({k:v for k,v in bound.arguments.items() if k not in ("m","g","glass")})
        return original(*args,**kwargs)
    # The fit-out's Log (cerroblanco_map.build) wraps these again by their signature: without it its records hold only
    # args and kwargs, and the fit-out stops with KeyError 'axis'.
    call.__signature__=signature
    setattr(module,name,call)
    return original


def linear_box(m,axis,run,across,z0,z1,paint):
    if run[1]-run[0] <= .01:return
    m.box(*C.lohi(axis,run,across,z0,z1),paint)


def floored(axis,run,across,z,slabs):
    """The parts of a run with a floor at height z beside it (across is a line just inside the wall): a slab whose top
    is z covers it there. The ground floor is everywhere."""
    if z<1:
        yield run
        return
    def covered(r):
        e,n=(r,across) if axis=="e" else (across,r)
        for s in slabs:
            if abs(s["z1"]-z)>.5 or not (s["e0"]<=e<=s["e1"] and s["n0"]<=n<=s["n1"]):continue
            if any(h[0]<=e<=h[1] and h[2]<=n<=h[3] for h in s["holes"]):continue
            return True
        return False
    start=None
    steps=np.arange(run[0],run[1]+.01,2.0)
    for r in steps:
        if covered(r):
            if start is None:start=r
        elif start is not None:
            yield start,r
            start=None
    if start is not None:yield start,run[1]


def intervals(lo,hi,holes):
    here=lo
    for a,b in sorted(holes):
        if a>here:yield here,min(a,hi)
        here=max(here,b)
    if here<hi:yield here,hi


def main():
    walls,parapets,flights,pictures,columns,slabs=[],[],[],[],[],[]
    originals=[(C,"wall",recorder(C,"wall",walls)),(C,"parapet_on",recorder(C,"parapet_on",parapets)),(P,"flight",recorder(P,"flight",flights)),(P,"picture",recorder(P,"picture",pictures)),(P,"column",recorder(P,"column",columns)),(P,"slab",recorder(P,"slab",slabs))]
    # Detail and hedge generation do not depend on distant landscape meshes.
    # Keep that separate while its own generator is being developed.
    original_backdrop=C.backdrop
    C.backdrop=lambda: (K.Model(),K.Model())
    try:base=C.build()
    finally:
        C.backdrop=original_backdrop
        for module,name,fn in originals:setattr(module,name,fn)
    grounds=base["cerroblanco_grounds"]
    assert "hedge" not in grounds.polygons, "The garden hedge's opaque ring has returned"
    ground_resource="models/maps/cerroblanco"
    ground_stage=HEDGE_STAGE/ground_resource
    ground_triangles=K.write_model(ground_stage,ground_resource,"cerroblanco_grounds",grounds)
    # floored() also takes every other level top at the first floor's height in the buildings, as its bounds: the West
    # Gallery's balcony is boxes and a ring, not a P.slab, and its plinth must stay along it. Not the slabs' own tops:
    # their bounds would take in a stairwell's edge, which the slab's hole leaves out.
    recorded=list(slabs)
    for points,normal in (item for items in base["cerroblanco_buildings"].polygons.values() for item in items):
        middle=np.mean(points,axis=0)
        if normal[2]>.99 and all(abs(q[2]-C.FLOOR1)<.01 for q in points) and not list(floored("e",(middle[0],middle[0]),middle[1],C.FLOOR1,recorded)):
            slabs.append({"e0":min(q[0] for q in points),"e1":max(q[0] for q in points),"n0":min(q[1] for q in points),"n1":max(q[1] for q in points),"z1":C.FLOOR1,"holes":[]})
    north,south,interior=K.Model(),K.Model(),K.Model()
    stats={"window_sills":0,"door_thresholds":0,"coping_runs":0,"stair_nosings":0,"gallery_spotlights":0}
    lights=[]
    for w in walls:
        if not w["outward"]:continue
        axis,run,across=w["axis"],w["run"],w["across"]
        sign=1 if w["outward"][0]=="+" else -1
        outer=max(across) if sign>0 else min(across)
        inner=min(across) if sign>0 else max(across)
        center_n=sum(run)/2 if axis=="n" else sum(across)/2
        m=north if center_n>=-900 else south
        def band(ra,rb,za,zb,paint,off=.6,width=.65):
            # Back on the façade, front off+width proud of it: from off, sills, heads, trims and plinths all stood
            # 0.1-0.4 inch clear of the wall, a slot of daylight behind each.
            linear_box(m,axis,(ra,rb),sorted((outer,outer+sign*(off+width))),za,zb,paint)
        for c,width,z0,z1 in w["windows"]:
            band(c-width/2-2,c+width/2+2,z0-1.1,z0+.15,P.FRAME,.4,1.8)
            band(c-width/2-1,c+width/2+1,z1,z1+.8,P.FRAME,.3,.9)
            stats["window_sills"]+=1
        for c,width,z0,z1 in w["doors"]:
            linear_box(m,axis,(c-width/2+2.5,c+width/2-2.5),across,z0+.04,z0+.13,P.STEEL)
            # Recessed continuous threshold grooves, at most 1/8 inch proud.
            for off in (-2,0,2):
                d=sum(across)/2+off
                linear_box(m,axis,(c-width/2+3,c+width/2-3),(d-.12,d+.12),z0+.131,z0+.16,P.FRAME)
            stats["door_thresholds"]+=1
        openings=list(w["doors"])+list(w["windows"])
        # Fine stone plinth and interior skirting, interrupted at openings: on the storeys the wall stands on (one that
        # starts at the first floor gets none on the ground floor: the cafe's upper room's wall drew a skirting and a
        # plinth line across the cafe's floor), and inside only where a floor meets the wall (none across a
        # double-height room's wall at the first floor's height). Outside likewise: a two-storey façade has no floor at
        # the first floor's height, and its plinth there was a dark line across the stone, 30 inches under the trim.
        storeys=[f for f in (0,C.FLOOR1) if w["z0"]-1<=f<w["z1"]-4] if w["z1"]>=350 else [w["z0"]]
        for floor in storeys:
            holes=[(c-width/2-1,c+width/2+1) for c,width,a,b in openings if a<floor+4 and b>floor]
            for a,b in intervals(run[0],run[1],holes):
                for c0,c1 in floored(axis,(a,b),outer+sign*8,floor,slabs):
                    band(c0,c1,floor+.3,floor+1.1,P.FRAME,.1,.18)
                for c0,c1 in floored(axis,(a,b),inner-sign*8,floor,slabs):
                    linear_box(interior,axis,(c0,c1),sorted((inner-sign*.7,inner)),floor+.05,floor+3.1,P.HONED)
        # Thin metal trim at the cladding change, clipped away from windows.
        split=w["split"]
        if w["lower"]!=w["upper_"] and w["z0"]<split<w["z1"]:
            holes=[(c-width/2-1,c+width/2+1) for c,width,a,b in openings if a<split+1 and b>split-1]
            for a,b in intervals(run[0],run[1],holes):band(a,b,split-.45,split+.45,P.FRAME,.13,.34)
    for p in parapets:
        axis,run,across,z=p["axis"],p["run"],p["across"],p["z"]+p["h"]+3
        center_n=sum(run)/2 if axis=="n" else sum(across)/2
        m=north if center_n>=-900 else south
        # 0.2 past the coping each side: parapet_on's coping is 2.5 proud on the outward side only, and at 2.7 both
        # sides the lip on the roof side hung 2.2 off the parapet.
        a=min(across)-(2.7 if p["outward"] in ("-n","-e") else .2)
        b=max(across)+(2.7 if p["outward"] in ("+n","+e") else .2)
        # A folded 1.25-inch cap retains a continuous silhouette at courtyard
        # distances; the old sub-inch edge broke into dark pixels in play.
        linear_box(m,axis,(run[0]-2.6,run[1]+2.6),(a,b),z-.15,z+1.25,P.FRAME)
        for cross in (a,b-.5):linear_box(m,axis,(run[0]-2.6,run[1]+2.6),(cross,cross+.5),z-1.15,z+1.25,P.FRAME)
        stats["coping_runs"]+=1
    # Circular drums and curved balcony have the same folded coping profile.
    for r,z in [(C.ROT_OUT+2, C.ROT_TOP+16),(C.ROT_UP,C.ROT_UP_TOP)]:
        P.ring(north,C.ROTUNDA,r-3,r+1.0,z-.15,z+1.25,outer=P.FRAME,inner=P.FRAME,top=P.FRAME,bottom=None,step=2,surface=None)
    # The last is the South Gallery canopy's front fascia (C.SG_CANOPY's f0 and g0 to its louvres, top lip + 2). It was
    # at the Portico callout's rectangle, -1060..510: 300 inches of it hung in the air west of the canopy, 70 east of it,
    # and the rest lay 1.85 over the canopy's roof, 20 behind the fascia.
    for e0,e1,n0,n1,z in [(-576,-570,-100,1050,326),(-588,-584,-100,1050,196),(-800,-716,-246,-240,326),(-760,180,-2440,-2436,420)]:
        m=north if n0>-900 else south
        m.box((e0-.4,n0-.4,z-.15),(e1+.4,n1+.4,z+1.25),P.FRAME)
    for f in flights:
        count=max(1,int(math.ceil((f["z_top"]-f["z_foot"])/f["max_rise"])))
        sign=1 if f["r_foot"]>f["r_top"] else -1
        step=abs(f["r_foot"]-f["r_top"])/count
        for k in range(count):
            r=f["r_top"]+sign*step*(k+1)
            z=f["z_top"]-(f["z_top"]-f["z_foot"])*k/count
            run=(f["a0"]+3,f["a1"]-3)
            # Two flush anti-slip grooves, not new collision geometry.
            for off in (1.2,2.05):
                rr=r-sign*off
                axis="e" if f["axis"]=="n" else "n"
                linear_box(interior,axis,run,(rr-.16,rr+.16),z+.025,z+.055,P.FRAME)
            stats["stair_nosings"]+=1
    # Proper low-profile drainage in perimeter service bands, away from cover.
    for axis,run,across in [("n",(-950,1050),(455,461)),("n",(-950,950),(-640,-634)),("e",(-1000,450),(-2444,-2438)),("n",(-970,640),(2073,2079))]:
        m=north if run[0]>-1000 else south
        linear_box(m,axis,run,across,.035,.10,P.FRAME)
        for pos in np.arange(run[0]+1,run[1]-1,2.5):
            linear_box(m,axis,(pos,pos+.5),(across[0]+.35,across[1]-.35),.105,.17,P.STEEL)
    # The art fixtures are placed from actual frame locations, not a decorative
    # grid; their forward vectors are written for the native spotlight importer.
    for index,p in enumerate(pictures):
        e,n=p["centre"]
        out=np.array([*p["facing"],0.],float)
        out/=np.linalg.norm(out)
        target=np.array([e,n,p["z"]],float)+out*2.5
        ceiling=158 if p["z"]<150 else 338
        if n<-1000 and e<480:ceiling=310
        pos=np.array([e,n,ceiling],float)+out*55
        axis=K.normalise(target-pos)
        side=np.cross(axis,(0,0,1))
        if np.linalg.norm(side)<.001:side=np.array([1,0,0])
        side=K.normalise(side)
        up=K.normalise(np.cross(side,axis))
        interior.oriented_box(pos,(side,axis,up),(3.8,7.5,3.8),P.FRAME)
        P.rod(interior,pos+(0,0,3),pos+(0,0,8),.55,P.STEEL,sides=8)
        face=pos+axis*4
        P.card(interior,P.LAMP,[face+side*x+up*y for x,y in [(-1.5,-1.5),(1.5,-1.5),(1.5,1.5),(-1.5,1.5)]],axis)
        lights.append({"name":f"Gallery art {index+1:02d}","position":K.vec(K.to_world(pos)),"target":K.vec(K.to_world(target)),"radius":240,"color":"1.4,1.25,1.04","inner":22,"outer":44})
        # Small engraved-label holder at the lower right of each frame.
        side=np.array([out[1],-out[0],0])
        label=np.array([e,n,p["z"]-p["h"]/2-7])+side*(p["w"]/2-6)+out*.8
        interior.oriented_box(label,(side,out,(0,0,1)),(11,.55,3),P.STEEL)
        stats["gallery_spotlights"]+=1
    for e,n,z in [(-612,k,163) for k in [90,380,660,940]]+[(-350,-2250,271),(100,-2250,271)]:
        m=north if n>-1000 else south
        m.cylinder((e,n),3.5,z-1,z,{"side":P.FRAME,"bottom":P.LAMP,"top":None},sides=16)
        lights.append({"name":f"Soffit {len(lights)+1:02d}","position":K.vec(K.to_world((e,n,z-2))),"target":K.vec(K.to_world((e,n,0))),"radius":220,"color":"1.25,1.12,.95","inner":25,"outer":55})
    # Fill the circular hedge with real leaf meshes. Its collision-only ring
    # still leaves all four openings clear and adds no visible green shell.
    garden_hedges=[]
    radius=C.GARDEN_R-20
    gap_half=math.degrees(55/C.GARDEN_R)
    for quarter in range(4):
        start,end=quarter*90+gap_half,(quarter+1)*90-gap_half
        span=math.radians(end-start)*radius
        count=math.ceil(span/110)
        length=span/count
        for index in range(count):
            angle=start+(end-start)*(index+.5)/count
            rad=math.radians(angle)
            position=(C.GARDEN[0]+radius*math.cos(rad),C.GARDEN[1]+radius*math.sin(rad),0)
            garden_hedges.append({"name":f"Garden hedge {quarter+1}-{index+1:02d}","model":P.HEDGE_MODEL,
                "position":K.vec(K.to_world(position)),"yaw":angle-90,
                "scale":K.vec((80/P.HEDGE_SIZE[0],(length+4)/P.HEDGE_SIZE[1],54/P.HEDGE_SIZE[2]))})
            # A reversed second mesh fills the spaces between the original
            # hedge's leaf cards without repeating the same twigs on top.
            fill_radius=radius+(5 if index%2 else -5)
            fill=(C.GARDEN[0]+fill_radius*math.cos(rad),C.GARDEN[1]+fill_radius*math.sin(rad),0)
            garden_hedges.append({"name":f"Garden hedge fill {quarter+1}-{index+1:02d}","model":P.HEDGE_MODEL,
                "position":K.vec(K.to_world(fill)),"yaw":angle+90,
                "scale":K.vec((78/P.HEDGE_SIZE[0],(length+14)/P.HEDGE_SIZE[1],56/P.HEDGE_SIZE[2]))})
    # The straight beds also use open leaf-card meshes. Keep their existing
    # silhouettes, and interleave another orientation instead of exposing a
    # green cuboid behind holes in the foliage.
    dressing=base["cerroblanco_dressing"]
    hedge_fill=[]
    for index,prop in enumerate(p for p in dressing.props if p["path"]==P.HEDGE_MODEL):
        e,n,z=prop["position"]
        yaw=prop["yaw"]
        sideways=2.5 if index%2 else -2.5
        if yaw%180==0:n+=sideways
        else:e+=sideways
        sx,sy,sz=prop["scale"]
        hedge_fill.append({"name":f"Linear hedge fill {index+1:03d}","model":P.HEDGE_MODEL,
            "position":K.vec(K.to_world((e,n,z))),"yaw":yaw+180,
            "scale":K.vec((sx*1.05,sy*.98,sz*1.04))})
    collision={"boxes":len(dressing.boxes),"hulls":len(dressing.hulls)}
    dressing.boxes=[]; dressing.hulls=[]
    models={"cerroblanco_detail_north":north,"cerroblanco_detail_south":south,"cerroblanco_detail_interior":interior,"cerroblanco_dressing_v2":dressing}
    written={}
    for name,model in models.items():
        C.configure(model)
        for paint in model.polygons:
            if paint in ["cb_honed","cb_paving","cb_travertine","cb_panel","cb_frame","cb_steel","cb_plaster","cb_white","cb_red","cb_teak"]:
                model.material_overrides[paint]=f"{MATERIAL}/{paint}.vmat"
        assert not model.boxes and not model.hulls
        written[name]=K.write_model(STAGE/RESOURCE,RESOURCE,name,model)
    report={"triangles":written,"ground_triangles":ground_triangles,"ground_collision":{"boxes":len(grounds.boxes),"hulls":len(grounds.hulls)},"original_dressing_collision_retained":collision,"details":stats,"lights":lights,"garden_hedges":garden_hedges,"hedge_fill":hedge_fill,"render_model_replacement":{"models/maps/cerroblanco/cerroblanco_dressing.vmdl":f"{RESOURCE}/cerroblanco_dressing_v2.vmdl"},"added_models":[f"{RESOURCE}/{n}.vmdl" for n in models if n!="cerroblanco_dressing_v2"],"files":[{"path":p.relative_to(STAGE).as_posix(),"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"bytes":p.stat().st_size} for p in sorted((STAGE/RESOURCE).glob("*")) if p.is_file()],"ground_files":[{"path":p.relative_to(HEDGE_STAGE).as_posix(),"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),"bytes":p.stat().st_size} for p in sorted(ground_stage.glob("*")) if p.is_file()]}
    (ROOT/"output/cerroblanco/geometry-manifest.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({"triangles":written,"details":stats,"lights":len(lights),"collision":collision}))


if __name__=="__main__":main()
