from pathlib import Path
import sys,re,json,collections,copy
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K, veridant_map as V, veridant_parts as P
from audit import keys
OUT=ROOT/'output/veridant/stair-geometry-fix';RESOURCE='models/maps/veridant/reception-stair-closure-v1'
parent=ROOT/'Assets/models/maps/veridant/veridant_buildings.vmdl';before=OUT/'before';before.mkdir(exist_ok=True)
assert not (before/'parent.vmdl').exists(), 'Already staged; inspect before rerunning'
text=parent.read_text();(before/'parent.vmdl').write_bytes(parent.read_bytes())
args=((-134,260),(-134,447),100,0,128)
old=K.Model();P.stone_stair(old,*args,sides=(True,False),name='reception stair')
new=K.Model();P.stone_stair(new,*args,sides=(True,False),name='reception stair',closed=True)
def polykey(mat,poly):return (mat,tuple(tuple(float(v) for v in p) for p in poly[0]))
existing=collections.Counter(polykey(mat,p) for mat,polys in old.polygons.items() for p in polys)
patch=K.Model();patch.uv_source_name='veridant_buildings'
for mat,polys in new.polygons.items():
    for p in polys:
        k=polykey(mat,p)
        if existing[k]:existing[k]-=1
        else:patch.polygon(mat,p[0],normal=p[1])
assert old.hulls.__repr__()==new.hulls.__repr__()
V.configure(patch);stage=OUT/'stage'/RESOURCE;stage.mkdir(parents=True,exist_ok=True);K.write_obj(stage/'closure.obj',patch,'veridant_buildings')
node=re.search(r'\{\s*_class = "RenderMeshFile".*?\n\s*\},',text,re.S)
addition=re.sub(r'name = "[^"]+"','name = "reception_stair_closure_v1"',node.group(),count=1)
addition=re.sub(r'filename = "[^"]+"',f'filename = "{RESOURCE}/closure.obj"',addition,count=1)
result=text[:node.end()]+'\n'+addition+text[node.end():]
assert result.split('PhysicsShapeList',1)[1]==text.split('PhysicsShapeList',1)[1]
(OUT/'stage/models/maps/veridant/veridant_buildings.vmdl').write_text(result)
report={'new_triangles':patch.triangle_count(),'physics_unchanged':True,'existing_render_meshes_unchanged':True,'old_stair_faces_present':True}
(OUT/'checks.json').write_text(json.dumps(report,indent=2));print(report)
