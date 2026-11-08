exec(open('output/veridant/gallery-rug-v1/prepare.py').read().split('old=K.Model()')[0])
m=K.Model();m.uv_source_name='veridant_buildings';B.build_into(m);V.configure(m);K.write_model(stage/SHARED,SHARED,'rug',m)
matdir=stage/'materials/veridant/gallery-rug-v1'
(matdir/'stripe.vmat').write_text((matdir/'weave.vmat').read_text().replace('[0.46 0.40 0.32 1]','[0.40 0.35 0.28 1]'))
