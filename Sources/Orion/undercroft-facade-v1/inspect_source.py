from pathlib import Path
p=Path('Assets/models/maps/orion/orion_launch_deck.obj');v=[];paint='';rows=[]
for l in p.read_text().splitlines():
 s=l.split()
 if not s:continue
 if s[0]=='v':v.append(tuple(map(float,s[1:])))
 elif s[0]=='usemtl':paint=s[1]
 elif s[0]=='f':
  pts=[v[int(t.split('/')[0])-1] for t in s[1:]]
  if all(abs(q[2]-900)<.001 for q in pts) and max(q[1] for q in pts)>200:rows.append((paint,pts))
print(rows[:30])
