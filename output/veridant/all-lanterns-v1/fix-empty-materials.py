from pathlib import Path
import json
root=Path.cwd();out=root/'output/veridant/all-lanterns-v1'
paths=[root/'Assets/models/maps/veridant/all-lanterns-v1/veridant_dress/without_lanterns_0.obj',root/'Assets/models/maps/veridant/hall-columns-v1/base_without_columns_0.obj']
stage=out/'repair';stage.mkdir(exist_ok=True);manifest=[]
for i,p in enumerate(paths):
 lines=p.read_text().splitlines(keepends=True);marks=[]
 for j,l in enumerate(lines):
  if l.startswith('usemtl '):marks.append(j)
 empty=[]
 for a,b in zip(marks,marks[1:]+[len(lines)]):
  if not any(x.startswith('f ') for x in lines[a:b]):empty.append(a)
 # Repack the OBJ after accumulated scoped removals. Retain every used corner's
 # position, UV, normal and material; discard only unreferenced records.
 from collections import defaultdict
 records={k:[] for k in ('v','vt','vn')};faces=[];material='';used={k:set() for k in records}
 for l in lines:
  w=l.split()
  if not w:continue
  if w[0] in records:records[w[0]].append(l)
  elif w[0]=='usemtl':material=w[1]
  elif w[0]=='f':
   corners=[tuple(int(x) if x else None for x in s.split('/')) for s in w[1:]]
   faces.append((material,corners))
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
 target=stage/f'{i}.obj';target.write_text(''.join(packed));manifest.append((str(target),str(p)));print(p,len(empty),{k:len(v) for k,v in used.items()})
script='foreach(var pair in new[]{'+','.join('('+json.dumps(a)+','+json.dumps(b)+')' for a,b in manifest)+'}){System.IO.File.Copy(pair.Item1,pair.Item2,true);Editor.AssetSystem.RegisterFile(pair.Item2);}return true;'
ex=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/all-lanterns/repair.cs');ex.write_text(script);(out/'repair.json').write_text(json.dumps({'path':str(ex)}))
