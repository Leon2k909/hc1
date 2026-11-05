from pathlib import Path
from native import ROOT
here=ROOT/'Sources/Riverdale/shared-cone-v1';here.mkdir(parents=True,exist_ok=True)
t=(Path(__file__).parent/'build.py').read_text();t=t.replace('shared-reel-v1','shared-cone-v1')
start=t.index('audit=dict(');end=t.index("(OUT/'existing-upgrade-audit.json')",start)
t=t[:start]+'''audit=dict(target='North lane cone at (300,2433)',reuse='models/maps/boxyard/traffic_cone_v2/traffic_cone.vmdl',existing_improvement_found=True,checked=['Boxyard traffic_cone_v2 approved and installed README','Riverdale live cone helper','Sources and notes for cone upgrades'],findings=['Riverdale still uses fourteen-sided solid cones','Approved Boxyard cone has hollow tip and underside, shaped rubber base, wear and three LODs','Reuse unchanged model and material, no duplicate replacement sources'])
'''+t[end:]
start=t.index('# Export only');end=t.index('def records(',start)
t=t[:start]+'''legacy=K.Model();Y.cone(legacy,'lane cone 0',(300,2433));R.configure(legacy);K.write_obj(OUT/'legacy-body.obj',legacy,'legacy_body')
K.write_obj(OUT/'legacy-full.obj',legacy,'legacy_full')
'''+t[end:]
t=t.replace('yard_without_reel','yard_without_cone')
start=t.index('radial=40/47.2');end=t.index("(OUT/'placement.json')",start)
t=t[:start]+'''radial=1.;axial=1.;scale=[1.,1.,1.];origin=[2433.,-300.,0.]
placement=dict(resource=audit['reuse'],world_scale=scale,world_position=origin,target_center=origin,rotation=[0,0,0],tail_faces_preserved=0)
'''+t[end:]
t=t.replace("shared.with_suffix('.obj')","shared.with_name('traffic_cone_lod0.obj')")
t=t.replace("new Vector3(2345,-145,65),Target=new Vector3(2420,-60,20),Fov=40f","new Vector3(2375,-343,36),Target=new Vector3(2433,-300,13),Fov=33f")
t=t.replace("new Vector3(2380,-118,43),Target=new Vector3(2420,-60,22),Fov=36f","new Vector3(2394,-326,24),Target=new Vector3(2433,-300,13),Fov=33f")
t=t.replace('Name="reel"','Name="cone"')
t=t.replace("models/maps/railhead/cable-drum-v1","models/maps/boxyard/traffic_cone_v2").replace("Assets/materials/railhead/cable-drum-v1","Assets/models/maps/boxyard/traffic_cone_v2")
(here/'build.py').write_text(t)
print('Cone reuse builder ready')
