from pathlib import Path
p=Path('output/veridant/court-stair-rail-v1/stage/models/maps/veridant/court-stair-rail-v1/base_without_court_rail_0.obj')
lines=p.read_text().splitlines(keepends=True)
records={k:[] for k in ('v','vt','vn')};faces=[];material='';used={k:set() for k in records}
for l in lines:
 w=l.split()
 if not w:continue
 if w[0] in records:records[w[0]].append(l)
 elif w[0]=='usemtl':material=w[1]
 elif w[0]=='f':
  corners=[tuple(int(x) if x else None for x in s.split('/')) for s in w[1:]];faces.append((material,corners))
  for c in corners:
   for k,index in zip(records,c):
    if index:used[k].add(index)
maps={k:{old:j+1 for j,old in enumerate(sorted(used[k]))} for k in records}
packed=['mtllib '+next(l.split(maxsplit=1)[1].strip() for l in lines if l.startswith('mtllib '))+'\n','o repacked\n']
for k in records:packed.extend(records[k][j-1] for j in sorted(used[k]))
prev=None
for mat,corners in faces:
 if mat!=prev:packed.append('usemtl '+mat+'\n');prev=mat
 packed.append('f '+' '.join('/'.join(str(maps[k][index]) if index else '' for k,index in zip(records,c)) for c in corners)+'\n')
p.write_text(''.join(packed));print('Repacked',len(faces),'faces without changing their corner data')
