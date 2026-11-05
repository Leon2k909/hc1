"""Adapt the guarded native installation to the three approved interior cabinets."""
from pathlib import Path
ROOT=Path(__file__).absolute().parents[3];HERE=Path(__file__).absolute().parent;OLD=ROOT/'Sources/Riverside/tower-roof-v1'
s=(OLD/'prepare_install.py').read_text()
for a,b in [('tower-roof-v1','interior-fridges-v1'),('legacy_roof','legacy_fridge'),('dressing_without_roof','store_without_fridges'),('riverside_dressing','riverside_store'),("'dressing.vmdl'","'store.vmdl'"),('len(cut)==4','len(cut)==42'),('removed_triangles=4','removed_triangles=42'),("position=m['position']","positions=m['positions']"),('dressing_vmdl_before','store_vmdl_before')]:s=s.replace(a,b)
(HERE/'prepare_install.py').write_text(s)
s=(OLD/'install.py').read_text()
for a,b in [('tower-roof-v1','interior-fridges-v1'),('tower_roof_v1/roof.vmdl','interior_fridges_v1/fridge.vmdl'),('Guard Tower Roofs','Interior Drinks Fridges'),('4676,3156,468','34152'),('riverside_dressing','riverside_store'),('RemovedOldTriangles=4','RemovedOldTriangles=42')]:s=s.replace(a,b)
a=s.index('var item=Editor.Mcp.SceneTools.CreateGameObject');b=s.index('Editor.Mcp.SceneTools.SaveScene();',a)
s=s[:a]+'''var items=new System.Collections.Generic.List<Guid>();
for(int k=0;k<3;k++)
{
    var item=Editor.Mcp.SceneTools.CreateGameObject(name:"Interior Drinks Fridge "+(k+1),parent:group.Id.ToString(),position:$"{760+k*34},-348,20",angles:"0,-90,0");
    Editor.Mcp.SceneTools.AddComponent(item.Id.ToString(),"ModelRenderer",new System.Text.Json.Nodes.JsonObject{["Model"]=model.ResourcePath,["Tint"]="1,1,1,1",["RenderType"]="On"});
    items.Add(item.Id);
}
'''+s[b:]
s=s.replace('Object=item.Id','Objects=items').replace('install-approved-tv-roof.cs','install-interior-fridges.cs')
(HERE/'install.py').write_text(s)
