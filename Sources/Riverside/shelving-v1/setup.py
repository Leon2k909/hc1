from pathlib import Path
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');HERE=Path(__file__).parent;prior=ROOT/'Sources/Riverside/register-v1'
def rename(s):return s.replace('C:/sbox-projects/hc1/register-review','C:/sbox-projects/hc1/shelving-review').replace('register-v1','shelving-v1').replace('legacy_register.vmdl','legacy_shelving.vmdl').replace('store_without_register','store_without_shelving').replace('register.vmdl','gondola.vmdl')
(HERE/'import.cs.txt').write_text(rename((prior/'import.cs.txt').read_text(encoding='utf-8')),encoding='utf-8')
(HERE/'native.py').write_text(rename((prior/'native.py').read_text(encoding='utf-8')),encoding='utf-8')
s=rename((prior/'isolated-review.cs.txt').read_text(encoding='utf-8'))
s=s.replace('new Vector3(-25,-27,22)','new Vector3(-90,-105,78)').replace('new Vector3(0,0,5)','new Vector3(0,0,27)').replace('FieldOfView=38','FieldOfView=47')
s=s.replace('new Vector3(-30,-40,55),150','new Vector3(-90,-90,110),330').replace('new Vector3(20,30,35),130','new Vector3(90,85,90),300')
(HERE/'isolated-review.cs.txt').write_text(s,encoding='utf-8')
s=rename((prior/'runtime-review.cs.txt').read_text(encoding='utf-8'))
s=s.replace('GameObject holder=null,item=null;','GameObject holder=null;var items=new System.Collections.Generic.List<GameObject>();')
start=s.index('  item=new GameObject(');end=s.index('  foreach(var variant',start)
s=s[:start]+'''  foreach(var pos in new[]{new Vector3(765,-140,20),new Vector3(875,-140,20),new Vector3(765,-270,20),new Vector3(875,-270,20)})
  {
   var item=new GameObject(false,"Temporary stocked shelf review");item.WorldPosition=pos;item.WorldRotation=Rotation.FromYaw(90);
   item.Components.Create<ModelRenderer>().Model=candidate;items.Add(item);
  }
'''+s[end:]
s=s.replace('item.Enabled=variant=="after"','foreach(var item in items)item.Enabled=variant=="after"')
s=s.replace('item?.Destroy();','foreach(var item in items)item.Destroy();')
s=s.replace('new Vector3(902,-153,90)','new Vector3(745,-218,85)').replace('new Vector3(935,-120,65.7f)','new Vector3(765,-140,47)').replace('camera.FieldOfView=38','camera.FieldOfView=60')
s=s.replace('frame<120','frame<80')
(HERE/'runtime-review.cs.txt').write_text(s,encoding='utf-8')
(HERE/'capture.py').write_text((prior/'capture.py').read_text(encoding='utf-8'),encoding='utf-8')
