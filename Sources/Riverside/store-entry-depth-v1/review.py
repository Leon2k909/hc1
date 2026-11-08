from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/riverside/store-entry-depth-v1';base=ROOT/'Sources/Riverside/storefront-depth-v1'
(HERE/'native.py').write_text((base/'native.py').read_text().replace('riverside/storefront-depth-v1','riverside/store-entry-depth-v1').replace('riverside-shopfront-review','riverside-shop-entry'))
sys.path.insert(0,str(HERE));import native
text=(base/'import.cs.txt').read_text().replace('storefront-depth-v1','store-entry-depth-v1').replace('storefront_depth_v1','store_entry_depth_v1');(HERE/'import.cs.txt').write_text(text);print(native.script(HERE/'import.cs.txt'))
for path in ('models/props/riverside/store_entry_depth_v1/frame.vmdl','models/props/riverside/store_entry_depth_v1/preview.vmdl','models/props/veridant/reception_doors_v1/leaf.vmdl'):print(native.call('asset_compile',dict(path=path)))
text=(base/'capture.cs.txt').read_text().replace('output/riverside/storefront-depth-v1/native','output/riverside/store-entry-depth-v1/native').replace('"Water Tower Tanks"','"Water Tower Tanks","Lucky Stop Glazed Windows"').replace('models/props/riverside/storefront_depth_v1/preview.vmdl','models/props/riverside/store_entry_depth_v1/preview.vmdl')
a=text.index('  replacement=new GameObject');b=text.index('\n  if(old.IsError',a)
text=text[:a]+'''  var group=new GameObject(false,"Shop entry review");group.Deserialize(System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(root,"output/riverside/store-entry-depth-v1/node.json"))).AsObject());replacement=group.GetComponent<ModelRenderer>();
  if(group.GetComponentsInChildren<ModelRenderer>().Any(r=>r.Model is null||r.Model.IsError))throw new Exception("Invalid reused leaf");
'''+text[b:]
text=text.replace('old.Materials.Concat(replacement.Model.Materials)','old.Materials.Concat(replacement.GameObject.GetComponentsInChildren<ModelRenderer>().SelectMany(r=>r.Model.Materials))')
a=text.index(' var views=');b=text.index('\n foreach(var after',a)
text=text[:a]+''' var views=new[]{("context",new Vector3(450,-235,100),new Vector3(640,-235,65),65f),("detail",new Vector3(550,-180,78),new Vector3(655,-235,58),65f)};'''+text[b:]
text=text.replace('ExistingMaterialsReused=true','ExistingMaterialsReused=true,ReusedDoorLeaves=2,AddedRenderers=3')
(HERE/'capture.cs.txt').write_text(text);print(native.script(HERE/'capture.cs.txt'))
