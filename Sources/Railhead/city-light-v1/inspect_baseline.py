from pathlib import Path
import re,json,collections
ROOT=Path(__file__).resolve().parents[3]
for doc in (ROOT/'Assets/models/maps/railhead').glob('railhead_dress_*.vmdl'):
 for rel in re.findall(r'filename\s*=\s*"([^\"]+\.obj)"',doc.read_text()):
  v=[];paint='';groups=collections.defaultdict(list)
  for l in (ROOT/'Assets'/rel).read_text().splitlines():
   s=l.split()
   if not s:continue
   if s[0]=='v':v.append(tuple(map(float,s[1:])))
   elif s[0]=='usemtl':paint=s[1]
   elif s[0]=='f':
    pts=[v[int(t.split('/')[0])-1] for t in s[1:]]
    if all(-590<p[0]<-500 and 20<p[1]<130 and 1280<p[2]<1310 for p in pts):groups[paint].append(pts)
  if groups:
   print(rel)
   for paint,rows in groups.items():
    pts=[p for r in rows for p in r];print(paint,len(rows),'min',[min(p[i] for p in pts) for i in range(3)],'max',[max(p[i] for p in pts) for i in range(3)])
