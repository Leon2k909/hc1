import bpy,json
from pathlib import Path
p=Path(__file__).resolve().parent
bpy.ops.wm.open_mainfile(filepath=str(p/'v_m4a1.2e216481e1b73b07.blend'))
out=[]
for o in bpy.data.objects:
    if o.type!='MESH' or not o.name.startswith('m4a1_'):continue
    weights={}
    mixed=0
    for v in o.data.vertices:
        g=sorted(v.groups,key=lambda g:g.weight,reverse=True)
        if not g:continue
        k=o.vertex_groups[g[0].group].name
        weights[k]=weights.get(k,0)+1
        mixed+=len([a for a in g if a.weight>.001])>1
    components=[]
    if o.name=='m4a1_v_m4a1_b':
        parent={}
        def root(x):
            parent.setdefault(x,x)
            while parent[x]!=x:x=parent[x]
            return x
        keys=[tuple(round(x,4)for x in v.co)for v in o.data.vertices]
        for f in o.data.polygons:
            a=root(keys[f.vertices[0]])
            for vi in f.vertices:parent[root(keys[vi])]=a
        groups={}
        for vi,k in enumerate(keys):groups.setdefault(root(k),[]).append(vi)
        for vs in groups.values():
            if len(vs)<10:continue
            components.append(dict(count=len(vs),bounds=[[min(o.data.vertices[v].co[i]for v in vs)for i in range(3)],[max(o.data.vertices[v].co[i]for v in vs)for i in range(3)]]))
    out.append(dict(object=o.name,weights=weights,mixed=mixed,components=components,bounds=[[min(v.co[i] for v in o.data.vertices)for i in range(3)],[max(v.co[i]for v in o.data.vertices)for i in range(3)]]))
(p/'base_inspect.json').write_text(json.dumps(out,indent=2))
