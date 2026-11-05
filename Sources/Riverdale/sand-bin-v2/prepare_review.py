from pathlib import Path
HERE=Path(__file__).parent
p=HERE/'runtime_review.cs.txt';t=p.read_text()
t=t.replace('architecture.Model=variant=="after"?Model.Load("models/maps/riverdale/sand-bin-v2/yard_without_bin.vmdl"):originalModel;','architecture.Model=Model.Load("models/maps/riverdale/sand-bin-v2/yard_without_bin.vmdl");\n replacement.Model=Model.Load(variant=="after"?"models/maps/riverdale/sand-bin-v2/sand_bin.vmdl":"models/maps/riverdale/sand-bin-v1/sand_bin.vmdl");')
t=t.replace('replacement.GameObject.Enabled=variant=="after";','replacement.GameObject.Enabled=true;')
p.write_text(t)
