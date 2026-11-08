from geometry import *
RES='models/maps/belltower/well-frame-v2';OUT=Path(tempfile.gettempdir())/'belltower-well-frame-v2';STAGE=OUT/'stage';MODEL=STAGE/'Assets'/RES
MODEL.mkdir(parents=True,exist_ok=True)
lods=[]
for i in range(3):lods.append(K.write_obj(MODEL/f'lantern_lod{i}.obj',build(i),f'lantern_lod{i}'))
L.RES=RES;L.MAPS=MAPS;(MODEL/'well_frame.vmdl').write_text(L.modeldoc())
print({'accepted_resource_staged':True,'lods':lods})
