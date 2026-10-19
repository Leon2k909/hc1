from pathlib import Path
import os

p=Path('Sources/Belltower/editor/capture-viewport.cs.txt')
s=p.read_text(encoding='utf8')
changes=[
('var trialSnapshots = new System.Collections.Generic.Dictionary<ModelRenderer,string>();',
 '''var trialSnapshots = new System.Collections.Generic.Dictionary<ModelRenderer,string>();
GameObject trialForest = null;
var originalObjects = scene.GetAllObjects(true).Select(o=>o.Id).ToHashSet();
var forestTrial = config["forest_trial"]?.GetValue<bool>()==true;'''),
('    foreach(var material in captureMaterials.Where(m=>m is not null && !m.IsError))',
 '''    if(forestTrial) captureMaterials.Add(Material.Load("materials/belltower/forest/forest_trees.vmat"));
    foreach(var material in captureMaterials.Where(m=>m is not null && !m.IsError))'''),
('''    using (scene.Push())
    {
        if(config["plaster_trial"]''',
 '''    using (scene.Push())
    {
        if(forestTrial)
        {
            if(scene.GetAllObjects(true).Any(o=>o.Name=="Distant woodland"))
                throw new InvalidOperationException("A saved woodland group is already present; use a saved-scene capture.");
            var data=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(root,"output/belltower/quality/forest-v1-staging/forest.json"))).AsObject();
            trialForest=scene.CreateObject(false);
            trialForest.Deserialize(data);
            trialForest.Flags |= GameObjectFlags.EditorOnly;
        }
        if(config["plaster_trial"]'''),
('var result = new { Capture=captureResult, TrialPlasterSlots=trialOverrides.Count,',
 '''var result = new { Capture=captureResult, TrialPlasterSlots=trialOverrides.Count,
        TrialForestSectors=trialForest is null ? 0 : trialForest.Children.Count,'''),
('''finally
{
    foreach(var item in trialOverrides)''',
 '''finally
{
    if(trialForest.IsValid())
    {
        using(scene.Push()) { trialForest.Destroy(); scene.ProcessDeletes(); }
        var forestRestored=scene.GetAllObjects(true).Select(o=>o.Id).ToHashSet().SetEquals(originalObjects);
        System.IO.File.WriteAllText(System.IO.Path.Combine(destination,name+"-forest-restore.json"),System.Text.Json.JsonSerializer.Serialize(new{ForestRestored=forestRestored}));
        if(!forestRestored) throw new InvalidOperationException("Forest preview cleanup differs; inspect before continuing.");
    }
    foreach(var item in trialOverrides)''')]
for old,new in changes:
    assert s.count(old)==1,old
    s=s.replace(old,new)
temp=p.with_suffix('.forest-writing')
temp.write_text(s,encoding='utf8',newline='\n')
os.replace(temp,p)

p=Path('output/belltower/quality/capture_views.py')
s=p.read_text(encoding='utf8')
old="parser.add_argument('--trial',action='store_true')"
assert s.count(old)==1
s=s.replace(old,old+"\nparser.add_argument('--forest-trial',action='store_true')")
old="'plaster_trial':args.trial}"
assert s.count(old)==1
s=s.replace(old,"'plaster_trial':args.trial,'forest_trial':args.forest_trial}")
temp=p.with_suffix('.forest-writing')
temp.write_text(s,encoding='utf8',newline='\n')
os.replace(temp,p)
print('Forest preview and capture options added atomically.')
