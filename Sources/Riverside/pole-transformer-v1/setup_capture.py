from pathlib import Path
root=Path(__file__).resolve().parents[3];here=Path(__file__).resolve().parent
s=(root/'Sources/Spillway/service-cabinet-v1/capture.cs.txt').read_text()
s=s.replace('output/spillway/service-cabinet-v1','output/riverside/pole-transformer-v1')
s=s.replace('models/maps/spillway/service-cabinet-v1/"+variant','models/maps/riverside/pole-transformer-v1/"+variant')
s=s.replace('new[]{"before","cabinet"}','new[]{"before","transformer"}')
s=s.replace('var cabinet=new GameObject(true,"Cabinet comparison")','var cabinet=new GameObject(true,"Transformer comparison")')
s=s.replace('floor.Components.Create<ModelRenderer>()','floor.WorldPosition=new Vector3(0,0,-16);floor.Components.Create<ModelRenderer>()')
s=s.replace('W(10,-90,135)','W(15,-50,85)').replace('W(78,-130,78)','W(54,-82,43)').replace('W(0,0,40)','W(0,-1,4)').replace('camera.FieldOfView=32','camera.FieldOfView=31')
(here/'capture.cs.txt').write_text(s)
