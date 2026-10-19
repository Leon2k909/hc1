"""Offline warehouse floor use, derived from saved collision and loading routes.

Produces numerical dust/rubber/polish masks and an unused material candidate.
Generated concrete albedo, all live assets and the existing AO bake stay intact.
This is not a native shader compiler, gameplay pathfinder or vehicle simulation.
"""
import argparse
import hashlib
import heapq
import itertools
import json
import math
from pathlib import Path
import re
import uuid
import zlib

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage, spatial

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'Sources/Lowtide/concrete'
OUT=ROOT/'output/lowtide/quality-pass/concrete-wear'
RESOURCE='materials/lowtide/concrete-wear'
MATERIAL=f'{RESOURCE}/lt_concrete_wear.vmat'
SHADER='shaders/hc1_lowtide_concrete_wear.shader'
MASK=f'{RESOURCE}/warehouse_use.png'
BASE_SHADER=ROOT/'Assets/shaders/hc1_lowtide_concrete.shader'
BASE_MATERIAL=ROOT/'Assets/materials/lowtide/interior/lt_concrete.vmat'


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding='utf-8',newline='\n')


def smooth(a,b,value):
    t=np.clip((value-a)/(b-a),0,1)
    return t*t*(3-2*t)


def rotation(pitch,yaw,roll):
    p,y,r=np.radians((pitch,yaw,roll))/2
    sp,cp,sy,cy,sr,cr=np.sin(p),np.cos(p),np.sin(y),np.cos(y),np.sin(r),np.cos(r)
    x,y,z,w=sr*cp*cy-cr*sp*sy,cr*sp*cy+sr*cp*sy,cr*cp*sy-sr*sp*cy,cr*cp*cy+sr*sp*sy
    return np.array(((1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)),
                     (2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)),
                     (2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y))))


def vector(block,key):
    value=re.search(r'\b'+key+r'\s*=\s*\[([^]]+)\]',block)
    if value is None: raise ValueError(f'Missing {key} in physics box')
    return np.asarray([float(v) for v in value[1].split(',')])


def hulls(path):
    # Generated OBJ elements have disjoint vertex indices. Recover those elements
    # from the actual faces, rather than treating all hulls as one bounding box.
    vertices=[]; faces=[]
    for line in path.read_text().splitlines():
        parts=line.split()
        if not parts: continue
        if parts[0]=='v':
            x,y,z=map(float,parts[1:]); vertices.append((-x,z,y))
        elif parts[0]=='f': faces.append([int(p.split('/')[0])-1 for p in parts[1:]])
    parent=list(range(len(vertices)))
    def root(i):
        while parent[i]!=i:
            parent[i]=parent[parent[i]]; i=parent[i]
        return i
    for face in faces:
        for i in face[1:]: parent[root(i)]=root(face[0])
    groups={}
    for face in faces:
        for i in face: groups.setdefault(root(i),set()).add(i)
    array=np.asarray(vertices)
    return [array[sorted(group)] for group in groups.values()]


def collision(side,settings):
    e0,e1,n0,n1=settings['bounds_plan_inches']
    z0,z1=settings['height_interval_inches']
    shapes=[]; sources={}; half='east' if side==1 else 'west'
    for name in (half,'dress_'+half):
        path=ROOT/f'Assets/models/maps/lowtide/lowtide_{name}.vmdl'
        sources[path.relative_to(ROOT).as_posix()]=sha(path)
        text=path.read_text()
        candidates=[]
        for index,match in enumerate(re.finditer(r'_class\s*=\s*"PhysicsShapeBox"([^{}]+)',text)):
            block=match[1]
            origin,angles,size=vector(block,'origin'),vector(block,'angles'),vector(block,'dimensions')
            corners=np.asarray(list(itertools.product((-1,1),repeat=3)))*size*.5
            world=corners@rotation(*angles).T+origin
            plan=np.column_stack((-world[:,1],world[:,0],world[:,2]))
            candidates.append((f'{name}:box:{index}',plan))
        for match in re.finditer(r'_class\s*=\s*"PhysicsHullFile"([\s\S]+?)import_filter',text):
            filename=re.search(r'filename\s*=\s*"([^"]+)"',match[1])[1]
            path=ROOT/'Assets'/filename
            sources[path.relative_to(ROOT).as_posix()]=sha(path)
            for index,points in enumerate(hulls(path)):
                candidates.append((f'{name}:hull:{path.stem}:{index}',points))
        for label,points in candidates:
            points=points.copy(); points[:,0]*=side
            if points[:,2].max()<=z0 or points[:,2].min()>=z1: continue
            minimum,maximum=points[:,:2].min(axis=0),points[:,:2].max(axis=0)
            if maximum[0]<e0 or minimum[0]>e1 or maximum[1]<n0 or minimum[1]>n1: continue
            unique=np.unique(points[:,:2],axis=0)
            if len(unique)<3: continue
            poly=unique[spatial.ConvexHull(unique).vertices]
            shapes.append(dict(label=label,polygon=poly.tolist()))
    return shapes,sources


def occupancy(shapes,bounds,size):
    width,height=size
    e0,e1,n0,n1=bounds
    canvas=Image.new('L',(width,height)); draw=ImageDraw.Draw(canvas)
    for shape in shapes:
        points=[((e-e0)/(e1-e0)*width-.5,(n1-n)/(n1-n0)*height-.5) for e,n in shape['polygon']]
        draw.polygon(points,fill=255)
    return np.asarray(canvas)>0


def to_pixel(points,bounds,size):
    e0,e1,n0,n1=bounds; w,h=size
    points=np.asarray(points)
    return np.stack(((points[...,0]-e0)/(e1-e0)*w-.5,(n1-points[...,1])/(n1-n0)*h-.5),-1)


def to_plan(pixel,bounds,size):
    e0,e1,n0,n1=bounds; w,h=size
    pixel=np.asarray(pixel)
    return np.stack((e0+(pixel[...,0]+.5)/w*(e1-e0),n1-(pixel[...,1]+.5)/h*(n1-n0)),-1)


def values(array,points,bounds):
    at=to_pixel(points,bounds,(array.shape[1],array.shape[0]))
    return ndimage.map_coordinates(array,np.stack((at[...,1],at[...,0])),order=1,mode='constant',cval=0)


def astar(clearance,start,end,minimum,bounds):
    h,w=clearance.shape
    size=(w,h)
    begin=np.rint(to_pixel(start,bounds,size)).astype(int)
    goal=np.rint(to_pixel(end,bounds,size)).astype(int)
    def valid(at):
        x,y=at
        return 0<=x<w and 0<=y<h and clearance[y,x]>=minimum
    if not valid(begin) or not valid(goal):
        raise ValueError(f'Route endpoint lacks {minimum}-inch clearance: {start} to {end}, '
                         f'clearances {values(clearance,np.asarray([start,end]),bounds).tolist()}')
    begin,goal=tuple(begin),tuple(goal)
    queue=[(0.,begin)]; costs={begin:0.}; previous={}
    while queue:
        _cost,at=heapq.heappop(queue)
        if at==goal: break
        for ox,oy in itertools.product((-1,0,1),repeat=2):
            if not (ox or oy): continue
            nxt=(at[0]+ox,at[1]+oy)
            if not valid(nxt): continue
            if ox and oy and (not valid((at[0]+ox,at[1])) or not valid((at[0],at[1]+oy))): continue
            cost=costs[at]+math.hypot(ox,oy)*(1+(minimum/max(clearance[nxt[1],nxt[0]],1))**2*.8)
            if cost>=costs.get(nxt,float('inf')): continue
            costs[nxt]=cost; previous[nxt]=at
            heapq.heappush(queue,(cost+math.dist(nxt,goal),nxt))
    if goal not in costs: raise ValueError(f'No route with {minimum}-inch clearance from {start} to {end}')
    path=[goal]
    while path[-1]!=begin: path.append(previous[path[-1]])
    return to_plan(np.asarray(path[::-1]),bounds,size)


def smooth_path(path,clearance,minimum,bounds):
    distance=np.r_[0,np.cumsum(np.linalg.norm(np.diff(path,axis=0),axis=1))]
    samples=np.arange(0,distance[-1],1.5)
    base=np.column_stack([np.interp(samples,distance,path[:,i]) for i in range(2)])
    for sigma in (14,10,6,3,0):
        candidate=ndimage.gaussian_filter1d(base,sigma,axis=0,mode='nearest') if sigma else base
        if values(clearance,candidate,bounds).min()>=minimum-1.5:
            return candidate,float(values(clearance,candidate,bounds).min()),sigma
    raise ValueError('No smoothed route passes the saved-collision clearance check')


def line_mask(path,bounds,size,width=1):
    canvas=Image.new('L',tuple(size)); draw=ImageDraw.Draw(canvas)
    draw.line([tuple(p) for p in to_pixel(path,bounds,size)],fill=255,width=width)
    return np.asarray(canvas)>0


def weighted_stroke(path,strength,bounds,size,step):
    canvas=Image.new('L',tuple(size)); draw=ImageDraw.Draw(canvas)
    points=to_pixel(path,bounds,size)
    for a,b,weight in zip(points[:-1],points[1:],(strength[:-1]+strength[1:])*.5):
        draw.line((tuple(a),tuple(b)),fill=max(1,round(float(weight)*255)),width=1)
    line=np.asarray(canvas)
    distance,nearest=ndimage.distance_transform_edt(line==0,sampling=step,return_indices=True)
    deposit=line[nearest[0],nearest[1]]/255
    return (1-smooth(1.8,4.1,distance))*deposit


def noise(shape,sigma,seed):
    rng=np.random.default_rng(seed)
    value=ndimage.gaussian_filter(rng.normal(size=shape).astype(np.float32),sigma,mode='reflect')
    return np.clip(.5+value/max(float(value.std()),1e-6)*.17,0,1)


def fields(shapes,settings,side):
    bounds=settings['bounds_plan_inches']; size=settings['atlas_cell_pixels']
    e0,e1,n0,n1=bounds; w,h=size
    step=((n1-n0)/h,(e1-e0)/w)
    occupied=occupancy(shapes,bounds,size)
    distance=ndimage.distance_transform_edt(~occupied,sampling=step)
    low_size=(round((e1-e0)/settings['path_grid_inches']),round((n1-n0)/settings['path_grid_inches']))
    low_occ=occupancy(shapes,bounds,low_size)
    clear=ndimage.distance_transform_edt(~low_occ,sampling=((n1-n0)/low_size[1],(e1-e0)/low_size[0]))
    polish=np.zeros((h,w),np.float32); scuff=np.zeros_like(polish); routes=[]
    broad=noise((h,w),42,173+side); fleck=noise((h,w),2.4,213+side)
    for route in settings['routes']:
        path=astar(clear,route['start'],route['end'],route['clearance'],bounds)
        path,minimum,sigma=smooth_path(path,distance,route['clearance'],bounds)
        line=line_mask(path,bounds,size)
        along_distance=ndimage.distance_transform_edt(~line,sampling=step)
        lane=(1-smooth(route['wear_radius']*.35,route['wear_radius']*1.5,along_distance))*route['strength']
        lane*=.50+broad*.50
        polish=np.maximum(polish,lane)
        # Scuffs break up along broad, gently curved paths. No tracks on sharp A* corners.
        tangent=np.gradient(path,axis=0)
        tangent/=np.maximum(np.linalg.norm(tangent,axis=1,keepdims=True),1e-6)
        turning=np.linalg.norm(np.gradient(tangent,axis=0),axis=1)/1.5
        smooth_enough=turning<1/80
        tire_segments=0
        if route['clearance']>=30:
            seed=zlib.crc32(route['name'].encode())+side
            rng=np.random.default_rng(seed)
            pulses=ndimage.gaussian_filter1d(rng.normal(size=len(path)),6,mode='reflect')
            pulses=.5+pulses/max(float(pulses.std()),1e-6)*.17
            fragments=smooth(.54,.76,pulses)
            fragments*=.22+.78*smooth(1/600,1/140,turning)
            runs=ndimage.label(smooth_enough)[0]
            for run in range(1,int(runs.max())+1):
                select=runs==run
                if select.sum()<45: continue
                segment=path[select]; heading=tangent[select]
                normal=np.column_stack((-heading[:,1],heading[:,0]))
                for offset in (-20,20):
                    track=segment+normal*offset
                    if values(distance,track,bounds).min()<6: continue
                    stroke=weighted_stroke(track,fragments[select],bounds,size,step)
                    # Patchy dry rubber, not a continuous painted racing line.
                    stroke*=smooth(.39,.72,broad)*(.28+.72*fleck)*.70
                    scuff=np.maximum(scuff,stroke)
                    tire_segments+=1
        routes.append(dict(**route,points=path.round(4).tolist(),minimum_clearance=minimum,
                           smoothing_sigma_samples=sigma,tire_segments=tire_segments))
        print(f'{side:+}: {route["name"]}: clearance {minimum:.1f} in, {tire_segments} restrained tire segments',flush=True)
    # Accumulated dust settles around storage edges, broken up by uneven cleaning.
    dust=(1-smooth(4,30,distance))*(.35+.65*broad)*(.75+.25*fleck)
    dust*=1-polish*.65
    # Mask all wear under the actual occupied footprint, with a small smooth transition.
    free=smooth(1.5,5,distance)
    yy,xx=np.mgrid[0:h,0:w]
    edge=np.minimum.reduce(((xx+.5)*step[1],(w-xx-.5)*step[1],(yy+.5)*step[0],(h-yy-.5)*step[0]))
    free*=smooth(0,16,edge)
    dust*=free; scuff*=free; polish*=free
    return np.stack((dust,scuff,polish),-1),occupied,routes


def staged_shader():
    base=BASE_SHADER.read_text()
    declaration=(SOURCE/'warehouse-use.hlsl').read_text()
    anchor='    float4 MainPs( PixelInput i ) : SV_Target0'
    assert base.count(anchor)==1
    out=base.replace(anchor,declaration+'\n'+anchor,1)
    apply='        m.Metalness = 0;'
    assert out.count(apply)==1
    out=out.replace(apply,'        ApplyWarehouseUse( i, m );\n'+apply,1)
    # A strict reversible insertion keeps the existing texture and floor-AO code intact.
    assert out.replace(declaration+'\n','',1).replace('        ApplyWarehouseUse( i, m );\n','',1)==base
    return out


def build(out=OUT):
    out=out.resolve()
    if not out.is_relative_to(ROOT/'output/lowtide/quality-pass'): raise ValueError('Offline output required')
    settings=json.loads((SOURCE/'wear-layout.json').read_text())
    previous=json.loads((ROOT/'output/lowtide/quality-pass/warehouse-floor/manifest.json').read_text())
    protected=dict(previous['protected'])
    for name in ('concrete_color.png','concrete_normal.png','concrete_rough.png','floor_contact.png','lt_concrete.vmat'):
        path=ROOT/'Assets/materials/lowtide/interior'/name
        protected[path.relative_to(ROOT).as_posix()]=sha(path)
    protected[BASE_SHADER.relative_to(ROOT).as_posix()]=sha(BASE_SHADER)
    assert all(sha(ROOT/p)==v for p,v in protected.items())
    sources={}; halves=[]; details={}
    for side in (1,-1):
        shapes,inputs=collision(side,settings); sources.update(inputs)
        data,occupied,routes=fields(shapes,settings,side)
        halves.append(data)
        details[str(side)]=dict(collision_shapes=shapes,routes=routes,
            occupied_pixels=int(occupied.sum()),range=[data.min(axis=(0,1)).tolist(),data.max(axis=(0,1)).tolist()],
            coverage_above_point1=(data>.1).mean(axis=(0,1)).tolist())
        out.mkdir(parents=True,exist_ok=True)
        Image.fromarray(occupied.astype(np.uint8)*255).save(out/f'occupied-{side:+}.png')
    stage=out/'stage'; target=stage/MASK; target.parent.mkdir(parents=True,exist_ok=True)
    Image.fromarray(np.rint(np.clip(np.concatenate(halves,axis=1),0,1)*255).astype(np.uint8)).save(target)
    write(stage/SHADER,staged_shader())
    material=BASE_MATERIAL.read_text()
    old='shader "shaders/hc1_lowtide_concrete.shader"'
    assert material.count(old)==1
    material=material.replace(old,f'shader "{SHADER}"',1)
    material=material.replace('    g_flConcreteScale',f'    TextureWarehouseUse "{MASK}"\n    g_flWarehouseUse "1"\n    g_flConcreteScale',1)
    write(stage/MATERIAL,material)
    remaps=[]
    for half in ('east','west'):
        path=ROOT/f'Assets/models/maps/lowtide/lowtide_{half}.vmdl'
        text=path.read_bytes()
        old=b'{ from = "rw_concrete.vmat" to = "materials/lowtide/interior/lt_concrete.vmat" }'
        new=('{ from = "rw_concrete.vmat" to = "'+MATERIAL+'" }').encode()
        assert text.count(old)==1
        relative=path.relative_to(ROOT/'Assets').as_posix()
        dest=stage/relative; dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(text.replace(old,new,1))
        remaps.append(dict(model=relative,slot='rw_concrete.vmat',before='materials/lowtide/interior/lt_concrete.vmat',after=MATERIAL,
                           before_sha256=sha(path),after_sha256=sha(dest)))
    for path in list(stage.rglob('*')):
        if path.is_file() and path.suffix in ('.shader','.vmat','.png'):
            rel=path.relative_to(stage).as_posix()
            write(Path(str(path)+'.meta'),json.dumps(dict(guid=str(uuid.uuid5(uuid.NAMESPACE_URL,rel))),indent=2)+'\n')
    for path in (Path(__file__),SOURCE/'wear-layout.json',SOURCE/'warehouse-use.hlsl',BASE_SHADER,BASE_MATERIAL):
        sources[path.relative_to(ROOT).as_posix()]=sha(path)
    assert all(sha(ROOT/p)==v for p,v in protected.items())
    manifest=dict(revision=settings['revision'],status='offline_candidate_not_installed',production_changed=False,
        sources=sources,protected=protected,settings=settings,details=details,remaps=remaps,
        channels=['dust','dry_rubber_scuff','traffic_polish'],new_geometry=0,new_material_slots=0,
        original_albedo_and_floor_contact_unchanged=True,base_shader_preserved_by_reversible_insertions=True,
        staged_files={p.relative_to(stage).as_posix():sha(p) for p in sorted(stage.rglob('*')) if p.is_file()},
        limitations=['Routes are a static wear layout, not a vehicle simulation','Native compilation, visual review, filtering and performance pending'])
    write(out/'manifest.json',json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(dict(stage=str(stage),files=len(manifest['staged_files']),protected=len(protected),
                         route_count=sum(len(d['routes']) for d in details.values())),indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUT)
    build(parser.parse_args().output)
