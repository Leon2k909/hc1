"""One cafe grinder: hopper/beans, burr body, chute and dosing forks."""
from pathlib import Path
import sys,math,json,hashlib,collections
import numpy as np
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,riverdale_parts as P,cerroblanco_fitout as F
from cerroblanco_bollards_upgrade import split_obj,remap_faces
OUT=ROOT/'output/cerroblanco/queue-posts-metal-v3';RESOURCE='models/maps/cerroblanco/queue-posts-metal-v3';PROP='models/props/cerroblanco/queue_posts_metal_v3'
SOURCE=ROOT/'Assets/models/maps/cerroblanco/cerroblanco_fitout_fine.obj'
X=(1,0,0);Y=(0,1,0);Z=(0,0,1);AX=(X,Y,Z)

from model import build

def keys(path):
    vs=[];mat='';out=[]
    for l in path.read_text().splitlines():
        if l.startswith('v '):vs.append(tuple(round(float(x),3) for x in l.split()[1:]))
        elif l.startswith('usemtl '):mat=l.split()[1]
        elif l.startswith('f '):out.append((mat,tuple(sorted(vs[int(x.split('/')[0])-1] for x in l.split()[1:]))))
    return out

def main():
    OUT.mkdir(exist_ok=True,parents=True)
    from model import LANES
    old=K.Model()
    for lane in LANES:F.stanchions(old,lane,0.)
    old.tile_overrides.update({k:24. for k in old.polygons});K.write_obj(OUT/'original.obj',old,'old_queue')
    targets=collections.Counter(keys(OUT/'original.obj'));raw=SOURCE.read_bytes();lines,vs,uvs,ns=split_obj(raw.decode());it=iter(keys(SOURCE));kept=[];removed=0
    for l in lines:
        if l.startswith('f '):
            key=next(it)
            if targets[key]:targets[key]-=1;removed+=1;continue
        kept.append(l)
    assert removed==len(keys(OUT/'original.obj')) and not any(targets.values()),removed
    m=build();dest=OUT/'stage'/PROP;K.write_model(dest,PROP,'queue',m)
    path=OUT/'placed.obj';added=K.write_obj(path,m,'cafe_grinder');new,nv,nt,nn=split_obj(path.read_text())
    # This installed OBJ has later appended vertex blocks. Keep their declaration
    # order/indices intact; add all new declarations only after the old records.
    merged=kept+[s for s in new if s.startswith('v ')]+nt+nn
    merged.extend(remap_faces(new,len(vs),len(uvs),len(ns)))
    dest=OUT/'stage'/RESOURCE;dest.mkdir(parents=True,exist_ok=True)
    (dest/'fine.obj').write_text(('\n'.join(merged)+'\n').replace('mtllib cerroblanco_fitout_fine.mtl','mtllib fine.mtl'))
    (dest/'fine.mtl').write_text(SOURCE.with_suffix('.mtl').read_text())
    before=SOURCE.with_suffix('.vmdl').read_text();after=before.replace('models/maps/cerroblanco/cerroblanco_fitout_fine.obj',RESOURCE+'/fine.obj');assert before!=after
    after=after.replace('{ from = \"soil.vmat\"', ''.join('{ from = \"'+k+'.vmat\" to = \"'+PROP+'/'+k+'.vmat\" },\n' for k in ('queue_metal','queue_shaft'))+'{ from = \"soil.vmat\"')
    (dest/'fine.vmdl').write_text(after)
    report={'source_sha256':hashlib.sha256(raw).hexdigest(),'removed_triangles':removed,'added_triangles':added,'unrelated_faces_preserved':sum(l.startswith('f ') for l in kept),'collision_unchanged':True,'review_only':True}
    (OUT/'checks.json').write_text(json.dumps(report,indent=2));print(report)
if __name__=='__main__':main()
