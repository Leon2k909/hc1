from pathlib import Path
ROOT=Path(__file__).absolute().parents[3];HERE=Path(__file__).absolute().parent
s=(ROOT/'Sources/Riverside/tower-roof-v1/context.cs.txt').read_text()
for a,b in [('tower-roof-v1','store-timber-steps-v1'),('tower_roof_v1/roof.vmdl','store_timber_steps_v1/steps.vmdl'),('tower_roof_v1/legacy_roof.vmdl','store_timber_steps_v1/legacy_steps.vmdl'),('tower_roof_v1/dressing_without_roof.vmdl','store_timber_steps_v1/store_without_steps.vmdl'),('models/maps/riverside/riverside_dressing.vmdl','models/maps/riverside/riverside_store.vmdl'),('Local(-210,-200,150),at,50f','Local(-90,-100,64),Local(15,0,12),52f'),('"close"','"entrance"'),('Local(-170,-200,-85),Local(0,0,-4),55f','Local(-40,80,42),Local(17,0,9),55f'),('"underside"','"detail"'),('CoolerMaterials','StepMaterials')]:s=s.replace(a,b)
s=s.replace('    ("detail",Local(-40,80,42),Local(17,0,9),55f,true)\n','')
(HERE/'context.cs.txt').write_text(s)
s=(ROOT/'Sources/Riverside/tower-roof-v1/import.cs.txt').read_text().replace('tower-roof-v1','store-timber-steps-v1').replace('tower_roof_v1','store_timber_steps_v1');(HERE/'import.cs.txt').write_text(s)
s=(ROOT/'Sources/Riverside/interior-fridges-v1/review.py').read_text()
for a,b in [('interior-fridges-v1','store-timber-steps-v1'),('interior_fridges_v1/fridge.vmdl','store_timber_steps_v1/steps.vmdl'),('interior_fridges_v1/legacy_fridge.vmdl','store_timber_steps_v1/legacy_steps.vmdl'),('item.Components.Create<ModelRenderer>().Model=cooler','newObject.Components.Create<ModelRenderer>().Model=cooler'),('item.Components.Create<ModelRenderer>().Model=oldCooler','newObject.Components.Create<ModelRenderer>().Model=oldCooler')]:s=s.replace(a,b)
(HERE/'review.py').write_text(s)
s=(ROOT/'Sources/Riverside/tower-roof-v1/verify.py').read_text().replace('tower-roof-v1','store-timber-steps-v1').replace('tower_roof_v1','store_timber_steps_v1').replace("f'roof_lod{lod}.obj'","f'steps_lod{lod}.obj'")
(HERE/'verify.py').write_text(s)
