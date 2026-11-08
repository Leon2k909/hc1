from pathlib import Path
ROOT=Path(__file__).absolute().parents[3];HERE=Path(__file__).absolute().parent;OLD=ROOT/'Sources/Riverside/yard-fence-v1'
def convert(s):
 for a,b in [('riverside/yard-fence-v1','riverdale/hydrant-v1'),('yard_fence_v1','hydrant_v1'),('models/props/riverside/','models/props/riverdale/'),('materials/riverside/hydrant_v1/','materials/riverdale/hydrant_v1/'),('legacy_fence','legacy_hydrant'),('dressing_without_fence','yard_without_hydrant'),('fence.vmdl','hydrant.vmdl'),('fence_lod','hydrant_lod'),('Assets/scenes/maps/Riverside/riverside.scene','Assets/scenes/maps/Riverdale/riverdale.scene'),('models/maps/riverside/riverside_dressing.vmdl','models/maps/riverdale/riverdale_yard_props.vmdl')]:s=s.replace(a,b)
 return s
for name in ('review.py','verify.py','import.cs.txt'):
 s=convert((OLD/name).read_text())
 if name=='review.py':s=s.replace("paths=[m['resource'],m['background'],'models/props/riverdale/hydrant_v1/legacy_hydrant.vmdl']","paths=[p[7:] for p in m['files'] if p.endswith('.vmat')]+[m['resource'],m['background'],'models/props/riverdale/hydrant_v1/previous.vmdl','models/props/riverdale/hydrant_v1/legacy_hydrant.vmdl']")
 s=s.replace('Compiled=3','Compiled=len(results)')
 (HERE/name).write_text(s)
s=convert((OLD/'context.cs.txt').read_text()).replace('"Moon"','"Sun", "Indirect Light"').replace('"Riverside"','"Riverdale"').replace('3.5f','2.5f')
s=s.replace('Local(-110,-40,64),Local(0,-250,30),75f','Local(-70,-55,64),Local(0,0,15),45f').replace('Local(-100,-235,64),Local(0,-250,34),62f','Local(-35,-25,31),Local(0,0,20),45f').replace('FenceMaterials','HydrantMaterials')
s=s.replace('    var written =','    await Task.Delay(2500, cancellationToken);\n    var written =')
s=s.replace('hydrant_v1/legacy_hydrant.vmdl','hydrant_v1/previous.vmdl')
(HERE/'context.cs.txt').write_text(s)
