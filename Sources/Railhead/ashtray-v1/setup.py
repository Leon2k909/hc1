"""Prepare native review of the saved Railhead play scene, without scene edits."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;template=ROOT/'Sources/Railhead/brick-pallet-v1'
native=(template/'native.py').read_text().replace('brick-pallet-v1','ashtray-v1').replace('railhead-pallet','railhead-ashtray');(HERE/'native.py').write_text(native)
(HERE/'capture.py').write_text((template/'capture.py').read_text())
runtime=(template/'runtime_review.cs.txt').read_text()
for old,new in [('brick-pallet-v1','ashtray-v1'),('brick_pallet.vmdl','ashtray.vmdl'),('east_without_pallet','east_without_ashtray'),('brick pallet','ashtray'),('1200,900','900,1200'),('Name="pallet",Eye=new Vector3(-1650,-1995,74),Target=new Vector3(-1580,-1884,21),Fov=44f','Name="ashtray",Eye=new Vector3(-936,-630,43),Target=new Vector3(-891,-601,20),Fov=34f')]:runtime=runtime.replace(old,new)
runtime=runtime.replace('Fov=34f}};', 'Fov=34f,Width=900,Height=1200},new {Name="head",Eye=new Vector3(-909,-613,49),Target=new Vector3(-891,-601,36),Fov=36f,Width=1200,Height=900}};')
runtime=runtime.replace('using var bitmap=new Bitmap(900,1200);','camera.CustomSize=new Vector2(view.Width,view.Height);\n  using var bitmap=new Bitmap(view.Width,view.Height);')
(HERE/'runtime_review.cs.txt').write_text(runtime)
verify=(template/'verify.py').read_text()
for old,new in [('brick-pallet-v1','ashtray-v1'),('east_without_pallet','east_without_ashtray'),("('pallet',)","('ashtray',)"),('RAILHEAD / BRICK PALLET','RAILHEAD / ASHTRAY')]:verify=verify.replace(old,new)
verify=verify.replace("('ashtray',)","('ashtray','head')")
(HERE/'verify.py').write_text(verify)
review=(template/'review.py').read_text().replace('brick-pallet-v1','ashtray-v1').replace("('brick_pallet','east_without_pallet')","('ashtray','east_without_ashtray')");(HERE/'review.py').write_text(review)
print('Review harness ready')
