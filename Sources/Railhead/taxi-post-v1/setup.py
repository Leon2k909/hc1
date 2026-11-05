from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;template=ROOT/'Sources/Railhead/brick-pallet-v1'
(HERE/'native.py').write_text((template/'native.py').read_text().replace('brick-pallet-v1','taxi-post-v1').replace('railhead-pallet','railhead-taxi-post'))
(HERE/'capture.py').write_text((template/'capture.py').read_text())
runtime=(template/'runtime_review.cs.txt').read_text().replace('brick-pallet-v1','taxi-post-v1').replace('brick_pallet.vmdl','taxi_post.vmdl').replace('east_without_pallet','east_without_taxi').replace('brick pallet','taxi post')
a=runtime.index(' var views=');b=runtime.index(' foreach(var variant',a)
runtime=runtime[:a]+''' var views=new[]{
 new {Name="sign",Eye=new Vector3(1265,-1513,104),Target=new Vector3(1180,-1488,92.3f),Fov=26f,Width=1200,Height=900},
 new {Name="whole",Eye=new Vector3(1335,-1540,90),Target=new Vector3(1180,-1488,51),Fov=32f,Width=900,Height=1200},
 new {Name="rear",Eye=new Vector3(1108,-1513,108),Target=new Vector3(1180,-1488,92.3f),Fov=30f,Width=1200,Height=900}};
'''+runtime[b:]
runtime=runtime.replace('using var bitmap=new Bitmap(1200,900);','camera.CustomSize=new Vector2(view.Width,view.Height);\n  using var bitmap=new Bitmap(view.Width,view.Height);')
(HERE/'runtime_review.cs.txt').write_text(runtime)
verify=(template/'verify.py').read_text()
for old,new in [('brick-pallet-v1','taxi-post-v1'),('east_without_pallet','east_without_taxi'),("('pallet',)","('sign','whole','rear')"),('RAILHEAD / BRICK PALLET','RAILHEAD / TAXI-RANK SIGN')]:verify=verify.replace(old,new)
(HERE/'verify.py').write_text(verify)
review=(template/'review.py').read_text().replace('brick-pallet-v1','taxi-post-v1').replace("('brick_pallet','east_without_pallet')","('taxi_post','east_without_taxi')");(HERE/'review.py').write_text(review)
print('Review harness ready')
