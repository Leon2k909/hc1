"""Locate complete old assemblies across canonical dressing meshes before replacement."""
from collections import Counter
import json
import map_kit as K
import railhead_stage_extinguisher as T

def main():
    legacy=T.old_function(); results={}
    for side in ('east','west'):
        lookup={}; totals={}; faces={}
        for i,args in enumerate(T.placements(side)):
            old=K.Model();legacy(old,*args)
            found,_=T.lookup_polygons(old)
            for key in found: lookup[key]=i
            totals[i]=old.triangle_count()
        wanted_positions={p for paint,face in lookup for p in face}
        counts=Counter();sparse={};v=0;paint=None
        path=T.ROOT/f'Assets/models/maps/railhead/railhead_dress_{side}.obj'
        for line in path.open('rb'):
            if line.startswith(b'v '):
                v+=1;p=T.point(line[2:].decode())
                if p in wanted_positions:sparse[v]=p
            elif line.startswith(b'usemtl '):paint=line.split()[1]
            elif line.startswith(b'f '):
                indices=[int(t.split(b'/')[0]) for t in line.split()[1:]]
                if all(i in sparse for i in indices):
                    key=(paint,frozenset(sparse[i] for i in indices))
                    if key in lookup:counts[lookup[key]]+=1
        results[side]=[{'placement':args,'found_triangles':counts[i],'expected':totals[i]}
                       for i,args in enumerate(T.placements(side))]
    out=T.OUT/'legacy-placement-audit.json';out.write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results))

if __name__=='__main__':main()
