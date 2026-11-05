from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
s=(ROOT/'Sources/Belltower/sack-pile-v2/build.py').read_text()
# Reuse the proven model/lathe imports, then author this model independently.
s=s[:s.index('HOOK=')]+"HOOK=(0.,1275.,0.)\nMAPS={'ashlar':'materials/belltower/ashlar.vmat'}\n\n"
s+='''def build(lod):
    m=K.Model();n=(48,32,16)[lod]
    D.lathe(m,(0,0),0,[(12.7,36),(13.,37),(13.,40),(11.8,42),(11.8,46),(10.8,48),(9.6,50),(9.3,55),(9.3,58),(8.9,60),(8.0,180),(8.1,184),(9.2,187),(9.2,190),(10.2,192),(12.6,196),(13.,198),(13.,201),(11.8,203),(7.0,204)],'ashlar',sides=n,caps=(True,True))
    contour=np.array([(-5,200),(5,200),(3.5,238),(20,239),(20,249),(3.5,250),(5,266),(-5,266),(-3.5,250),(-20,249),(-20,239),(-3.5,238)],float)
    inner=[]
    for i,p in enumerate(contour):
        a=K.normalise(p-contour[i-1]);b=K.normalise(contour[(i+1)%len(contour)]-p)
        na=np.array((-a[1],a[0]));nb=np.array((-b[1],b[0]));inner.append(p+(na+nb)*.6/(1+np.dot(na,nb)))
    inner=np.array(inner)
    def at(p,y):return np.array((p[0],y,p[1]))
    # Ear clipping keeps the concave cross faces solid without incorrect fan triangles.
    indices=list(range(len(inner)));tri=[]
    cross=lambda a,b:float(a[0]*b[1]-a[1]*b[0])
    while len(indices)>3:
        for j,b in enumerate(indices):
            a,c=indices[j-1],indices[(j+1)%len(indices)]
            if cross(inner[b]-inner[a],inner[c]-inner[b])<=1e-9:continue
            if any(all(cross(inner[v]-inner[u],inner[k]-inner[u])>=-1e-8 for u,v in ((a,b),(b,c),(c,a))) for k in indices if k not in (a,b,c)):continue
            tri.append((a,b,c));indices.pop(j);break
        else:raise RuntimeError('Cross face triangulation failed')
    tri.append(tuple(indices))
    for sign in (-1,1):
        for ids in tri:D.outward(m,'ashlar',[at(inner[k],sign*4) for k in ids],(0,sign,0))
        for k,p in enumerate(contour):
            q=(k+1)%len(contour);edge=contour[q]-p;normal=np.array((edge[1],0,-edge[0]))
            D.outward(m,'ashlar',[at(inner[k],sign*4),at(inner[q],sign*4),at(contour[q],sign*3.4),at(p,sign*3.4)],normal+np.array((0,sign,0)))
    for k,p in enumerate(contour):
        q=(k+1)%len(contour);edge=contour[q]-p
        D.outward(m,'ashlar',[at(p,-3.4),at(contour[q],-3.4),at(contour[q],3.4),at(p,3.4)],(edge[1],0,-edge[0]))
    for sign in (-1,1):
        F.turned(m,(0,sign*4,244),(0,sign,0),(1,0,0),[(5.2,0),(5.3,.25),(4.6,.75),(3.8,.95)],'ashlar',segments=(24,16,10)[lod])
    D.configure(m);m.material_overrides.update(MAPS);return m

'''
# Use the original review staging code, not the now-installed sack builder's main.
t=(ROOT/'Sources/Belltower/dish-lamp-v2/prepare.py').read_text() # only used as a documented source reference
source=(ROOT/'Sources/Belltower/market-cross-v2/staging-template.txt').read_text() if (HERE/'staging-template.txt').exists() else ''
(HERE/'geometry.py').write_text(s)
