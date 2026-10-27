import json,collections
from pathlib import Path
folder=Path.cwd()/'Assets/models/maps/forestbase/fir';rows=[]
for variant in 'abc':
 for lod in ('lod0','lod1','distant','horizon'):
  v=[];f=[];mat=None;counts=collections.Counter()
  for line in (folder/f'fir_{variant}_{lod}.obj').read_text().splitlines():
   s=line.split()
   if not s:continue
   if s[0]=='v':v.append(tuple(map(float,s[1:4])))
   elif s[0]=='usemtl':mat=s[1]
   elif s[0]=='f':
    ids=[int(x.split('/')[0])-1 for x in s[1:]];counts[mat]+=len(ids)-2
    if mat.endswith('_twig'):f.append(ids)
  parents=list(range(len(v)))
  def find(i):
   while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
   return i
  for face in f:
   for a in face[1:]:parents[find(a)]=find(face[0])
  islands=collections.Counter()
  for face in f:islands[find(face[0])]+=len(face)-2
  rows.append(dict(variant=variant,lod=lod,triangles=dict(counts),leafIslands=len(islands),islandTriangleCounts=dict(collections.Counter(islands.values()))))
print(json.dumps(rows,indent=2))
(Path.cwd()/'output/forestbase/crown-stage/source-analysis.json').write_text(json.dumps(rows,indent=2)+'\n')
