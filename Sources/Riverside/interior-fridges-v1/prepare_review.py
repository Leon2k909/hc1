"""Reuse the established disposable-scene renderer with three approved cabinets."""
from pathlib import Path
ROOT=Path(__file__).absolute().parents[3];HERE=Path(__file__).absolute().parent
s=(ROOT/'Sources/Riverside/tower-roof-v1/context.cs.txt').read_text()
s=s.replace('tower-roof-v1','interior-fridges-v1').replace('tower_roof_v1/roof.vmdl','interior_fridges_v1/fridge.vmdl').replace('tower_roof_v1/legacy_roof.vmdl','interior_fridges_v1/legacy_fridge.vmdl')
a=s.index('var foot =');b=s.index('var scene =',a)
s=s[:a]+'''var views=new (string Name,Vector3 Eye,Vector3 Target,float Fov,bool Cooler)[]
{
 ("aisle",new Vector3(701,-285,84),new Vector3(790,-348,57),60f,true),
 ("detail",new Vector3(761,-300,82),new Vector3(789,-348,57),62f,true)
};
'''+s[b:]
s=s.replace('GameObject newObject, oldObject;','var newObjects=new System.Collections.Generic.List<GameObject>();')
a=s.index('        var low=');b=s.index('        var holder =',a)
s=s[:a]+'''        var low=scene.GetAllComponents<ModelRenderer>().Single(r=>r.Model?.ResourcePath?.Equals("models/maps/riverside/riverside_store.vmdl",StringComparison.OrdinalIgnoreCase)==true);
        low.Model=Model.Load("models/props/riverside/interior_fridges_v1/store_without_fridges.vmdl");
        for(int k=0;k<3;k++)
        {
            var pos=new Vector3(760+k*34,-348,20);
            var item=new GameObject(false,"Interior drinks cabinet "+k);item.WorldPosition=pos;item.WorldRotation=Rotation.FromYaw(-90);
            item.Components.Create<ModelRenderer>().Model=cooler;newObjects.Add(item);
        }
'''+s[b:]
s=s.replace('newObject.Enabled = variant == "after";','foreach(var item in newObjects){item.Components.GetAll<ModelRenderer>(FindMode.EverythingInSelfAndDescendants).Single().Model=variant == "after"?cooler:oldCooler;item.Enabled=true;}').replace('oldObject.Enabled = variant == "before";','')
s=s.replace('"TV aerial review"','"Interior fridge review"').replace('CoolerMaterials =','CabinetMaterials =')
(HERE/'context.cs.txt').write_text(s)
