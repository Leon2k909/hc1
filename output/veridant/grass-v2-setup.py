from pathlib import Path
p=Path('output/veridant/garden-grass-blades-v1/prepare.py').read_text().replace('garden-grass-blades-v1','garden-grass-blades-v2').replace('veridant_short_garden_grass_v1','veridant_short_garden_grass_v2')
a=p.index(" verts=data[");b=p.index(' result=[',a)
p=p[:a]+''' verts=data['v'];parents=list(range(len(verts)))
 def find(x):
  while parents[x]!=x:x=parents[x]
  return x
 for face in faces:
  ids=[c[0]-1 for c in face]
  for j in ids[1:]:parents[find(j)]=find(ids[0])
 groups={}
 for j in range(len(verts)):groups.setdefault(find(j),[]).append(j)
 for ids in groups.values():
  ids.sort();rootx=(verts[ids[0]][0]+verts[ids[1]][0])*.5;rootz=(verts[ids[0]][2]+verts[ids[1]][2])*.5
  for j in range(0,len(ids)-1,2):
   ia,ib=ids[j:j+2];a,b=verts[ia],verts[ib];mid=tuple((x+y)*.5 for x,y in zip(a,b))
   for idx,pt in ((ia,a),(ib,b)):
    q=tuple(c+(x-c)*.32 for x,c in zip(pt,mid))
    verts[idx]=(rootx+(q[0]-rootx)*.65,q[1],rootz+(q[2]-rootz)*.65)
  tip=ids[-1];x,y,z=verts[tip];verts[tip]=(rootx+(x-rootx)*.65,y,rootz+(z-rootz)*.65)
'''+p[b:]
out=Path('output/veridant/garden-grass-blades-v2');out.mkdir(exist_ok=True);(out/'prepare.py').write_text(p)
