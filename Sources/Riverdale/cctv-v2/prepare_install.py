"""Prepare the native install transaction. This script never applies it."""
from pathlib import Path
from collections import Counter
import hashlib, json, ast
import native
import sys
sys.path.insert(0,str(native.ROOT/'Tools'))
import riverdale_camera as camera
import riverdale_splice as splice

ROOT=native.ROOT
OUT=native.OUT
STAGE=OUT/'install-stage'
STAGE.mkdir(parents=True,exist_ok=True)
manifest=json.loads((OUT/'manifest.json').read_text())
changes=[]
geometry=[]

def stage(relative, data, expected=None):
    target=ROOT/relative
    current=target.read_bytes()
    digest=hashlib.sha256(current).hexdigest()
    if expected: assert digest==expected, f'Published source changed: {relative}'
    staged=STAGE/relative
    staged.parent.mkdir(parents=True,exist_ok=True)
    staged.write_bytes(data)
    changes.append(dict(relative=relative, source=str(target), staged=str(staged), sha256=digest))

for entry in manifest['models']:
    name=entry['name']
    published_obj=ROOT/'Assets/models/maps/riverdale'/f'{name}.obj'
    snapshot=published_obj.read_bytes()
    snapshot_hash=hashlib.sha256(snapshot).hexdigest()
    snapshot_path=STAGE/f'{name}-source.obj'
    snapshot_path.write_bytes(snapshot)
    header,faces=splice.read_obj(snapshot_path)
    old=Counter(splice.read_obj(OUT/'stage'/f'{name}-old.obj')[1])
    new_path=OUT/'stage'/f'{name}-new.obj'
    new=Counter(splice.read_obj(new_path)[1]) if entry['new_camera_triangles'] else Counter()
    current=Counter(faces)
    assert not old-current, f'Original camera geometry changed or was already replaced: {name}'
    replacement=list((current-old).elements())+list(new.elements())
    rebuilt=STAGE/f'{name}-installed.obj'
    splice.write_obj(rebuilt,header,replacement)
    assert Counter(splice.read_obj(rebuilt)[1])-new==current-old
    geometry.append(dict(model=name,removed_camera_faces=sum(old.values()),added_camera_faces=sum(new.values()),
                         other_faces_preserved=True,source_sha256=snapshot_hash))
    for ext in ('obj','mtl','vmdl'):
        published=ROOT/'Assets/models/maps/riverdale'/f'{name}.{ext}'
        data=rebuilt.read_bytes() if ext=='obj' else published.read_bytes()
        # Material edits can occur independently of mesh edits. Always preserve
        # the current published remaps and MTL, adding only the camera slots.
        if ext=='vmdl' and entry['new_camera_triangles']:
            assert b'rv_cam_' not in data, 'Camera material slots already installed; inspect before retrying.'
            lines=data.decode('utf-8').splitlines(keepends=True)
            last=max(i for i,line in enumerate(lines) if 'from = ' in line and 'to = ' in line)
            eol='\r\n' if lines[last].endswith('\r\n') else '\n'
            lines[last]=lines[last].rstrip().rstrip(',')+','+eol
            additions=[f'\t\t\t\t\t\t\t{{ from = "{paint}.vmat" to = "materials/riverdale/cctv_v2/{paint}.vmat" }}' for paint in sorted(camera.MATERIALS)]
            lines[last+1:last+1]=[line+(',' if i<len(additions)-1 else '')+eol for i,line in enumerate(additions)]
            data=''.join(lines).encode('utf-8')
        if ext=='mtl' and entry['new_camera_triangles']:
            data+=b'\n'+''.join(f'newmtl {paint}\nKd 1 1 1\nd 1\n' for paint in sorted(camera.MATERIALS)).encode('utf-8')
        expected=snapshot_hash if ext=='obj' else None
        stage(f'Assets/models/maps/riverdale/{name}.{ext}',data,expected)

hall=ROOT/'Tools/riverdale_hall.py'
data=hall.read_bytes()
text=data.decode('utf-8')
start=text.index('def camera( d, fine, face, s, z, target ):')
end=text.index('\ndef horn(',start)
new='''def camera( d, fine, face, s, z, target ):
    """ Detailed weatherproof camera, retaining the established anchors and aim. """
    from riverdale_camera import camera as draw_camera
    return draw_camera( d, fine, face, s, z, target )

'''
hall_replacement=text[:start]+new+text[end:]
ast.parse(hall_replacement)
stage('Tools/riverdale_hall.py',hall_replacement.encode('utf-8'))

path=ROOT/'Tools/riverdale_map.py'
text=path.read_bytes().decode('utf-8')
old='''        if paint.startswith( "rv_" ):
            model.material_overrides[paint] = f"{RM.RESOURCE_DIR}/{paint}.vmat"'''
new='''        if paint.startswith( "rv_cam_" ):
            model.material_overrides[paint] = f"materials/riverdale/cctv_v2/{paint}.vmat"
            model.tile_overrides[paint] = 7.0
        elif paint.startswith( "rv_" ):
            model.material_overrides[paint] = f"{RM.RESOURCE_DIR}/{paint}.vmat"'''
assert text.count(old)==1
map_replacement=text.replace(old,new)
ast.parse(map_replacement)
stage('Tools/riverdale_map.py',map_replacement.encode('utf-8'))

(OUT/'install-plan.json').write_text(json.dumps(changes,indent=2)+'\n')
(OUT/'install-geometry.json').write_text(json.dumps(geometry,indent=2)+'\n')
script='''// Run only after the user approves the reviewed camera.
var root=Sandbox.Project.Current.GetRootPath();
var folder=System.IO.Path.Combine(root,"output/riverdale/cctv-v2");
var initialScene=Editor.SceneEditorSession.Active?.Scene?.Id;
var initialGame=Game.ActiveScene?.Id;
var initialPlay=Game.IsPlaying;
var plan=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"install-plan.json"))).AsArray();
string Sha(string path)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(path))).ToLowerInvariant();
// Validate every source and candidate before the first write.
foreach(var change in plan) {
 var source=change["source"].GetValue<string>();
 if(Sha(source)!=change["sha256"].GetValue<string>()) throw new InvalidOperationException("Source changed since review: "+source);
 if(!System.IO.File.Exists(change["staged"].GetValue<string>())) throw new InvalidOperationException("Missing staged source");
}
var backup=System.IO.Path.Combine(folder,"retired");
foreach(var change in plan) {
 var destination=System.IO.Path.Combine(backup,change["relative"].GetValue<string>());
 if(System.IO.File.Exists(destination)) throw new InvalidOperationException("Backup already exists; inspect installation before retrying.");
 System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(destination));
 System.IO.File.Copy(change["source"].GetValue<string>(),destination);
}
foreach(var change in plan) {
 var path=change["source"].GetValue<string>();
 System.IO.File.Copy(change["staged"].GetValue<string>(),path+".cctv-writing",true);
 System.IO.File.Move(path+".cctv-writing",path,true);
}
var report=new { Installed=true, Files=plan.Count,
 SceneUnchanged=Editor.SceneEditorSession.Active?.Scene?.Id==initialScene && Game.ActiveScene?.Id==initialGame,
 PlayStateUnchanged=Game.IsPlaying==initialPlay, Game.IsPlaying };
System.IO.File.WriteAllText(System.IO.Path.Combine(folder,"installed.json"),System.Text.Json.JsonSerializer.Serialize(report));
return report;
'''
(OUT/'install.cs.txt').write_text(script)
print(json.dumps(dict(Ready=True,Applied=False,Files=[x['relative'] for x in changes]),indent=2))
