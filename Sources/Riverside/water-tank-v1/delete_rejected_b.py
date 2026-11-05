"""Delete the explicitly rejected full-tower B candidate and its dedicated worktree."""
from pathlib import Path
import sys,json,shutil,subprocess,hashlib,psutil,os
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/riverside/water-tank-v1'
REVIEW=Path('C:/sbox-projects/hc1/water-tower-review')
assert ROOT.resolve()==Path('C:/sbox-projects/hc1/forked-shooter-main')
assert REVIEW.resolve()==Path('C:/sbox-projects/hc1/water-tower-review') and not REVIEW.is_junction() and not REVIEW.is_symlink()
assert json.loads((OUT/'installed.json').read_text())['Installed']
allowed=('Assets/materials/riverside/water-tower-v1/','Assets/models/maps/riverside/water-tower-v1/','Sources/Riverside/water-tower-v1/','output/riverside/water-tower-v1/')
def git(*args):
    r=subprocess.run(['rtk','proxy','git',*args],cwd=REVIEW,capture_output=True,text=True)
    assert r.returncode==0,r.stderr;return r.stdout
status=git('status','--porcelain=v1','--untracked-files=all').splitlines()
assert all(line.startswith('?? ') and line[3:].startswith(allowed) for line in status),status[:10]
ignored=[s for s in git('ls-files','--others','--ignored','--exclude-standard','-z').split('\0') if s]
assert all(s.startswith(allowed) for s in ignored),ignored
for p in psutil.process_iter(['name']):
    if p.pid==os.getpid():continue
    if p.info['name'].lower() in ('python.exe','blender.exe'):
        assert not any(str(REVIEW).lower() in a.lower().replace('/','\\') for a in p.cmdline()),'B still has an active renderer/builder.'
scene=ROOT/'Assets/scenes/maps/Riverside/riverside.scene'
assert 'water-tower-v1' not in scene.read_text()
sys.path.insert(0,str(ROOT/'Sources/Spillway/hose-coil-v2'));from native import Editor
with Editor() as e:
    assets=e.script(r'''var project=System.IO.Path.GetFullPath(Sandbox.Project.Current.GetRootPath());
if(!project.Equals(@"C:\sbox-projects\hc1\forked-shooter-main",StringComparison.OrdinalIgnoreCase))throw new Exception("Wrong project");
var roots=new[]{"Assets/models/maps/riverside/water-tower-v1","Assets/materials/riverside/water-tower-v1"};
var removed=new System.Collections.Generic.List<string>();
foreach(var relative in roots)
{
    var folder=System.IO.Path.GetFullPath(System.IO.Path.Combine(project,relative));
    if(!folder.StartsWith(project+System.IO.Path.DirectorySeparatorChar,StringComparison.OrdinalIgnoreCase)||!folder.EndsWith("water-tower-v1"))throw new Exception("Unsafe B deletion path");
    if(!System.IO.Directory.Exists(folder))continue;
    if(System.IO.Directory.EnumerateDirectories(folder).Any())throw new Exception("Unexpected child directory in B assets");
    foreach(var file in System.IO.Directory.EnumerateFiles(folder)){removed.Add(System.IO.Path.GetRelativePath(project,file));System.IO.File.Delete(file);}
    System.IO.Directory.Delete(folder,false);
}
return new{DeletedBAssets=removed.Count,Files=removed,AExists=System.IO.File.Exists(System.IO.Path.Combine(project,"Assets/models/props/riverside/water_tank_v1/tank.vmdl"))};''','delete-rejected-full-tower-b.cs')
    assert assets['AExists']
    prior=OUT/'deleted-b-assets.json'
    if assets['DeletedBAssets']==0 and prior.exists():assets=json.loads(prior.read_text())
    else:prior.write_text(json.dumps(assets,indent=2))
# Each resolved recursive removal is checked against these exact task-owned directories first.
folders=[ROOT/'Sources/Riverside/water-tower-v1',ROOT/'output/riverside/water-tower-v1',ROOT/'output/riverside/tower-candidate-comparison-20261104']
deleted=[]
for target in folders:
    expected=((ROOT/'output').resolve()/'riverside'/target.name) if target.is_relative_to(ROOT/'output') else target.absolute()
    resolved=target.resolve()
    assert resolved==expected and resolved.parent==expected.parent and not target.is_junction() and not target.is_symlink()
    if target.exists():shutil.rmtree(resolved);deleted.append(str(resolved))
for rel in ['Sources/Riverside/water-tank-v1/compare_candidates.py','Sources/Riverside/water-tank-v1/compose_candidate_comparison.py','docs/notes/riverside-full-water-tower-v1-review-20261104.md']:
    target=ROOT/rel
    if target.exists():target.unlink();deleted.append(str(target))
# Dedicated B checkout has only the enumerated B files; remove it through Git, not a computed shell deletion.
r=subprocess.run(['rtk','proxy','git','worktree','remove','--force',str(REVIEW)],cwd=ROOT,capture_output=True,text=True)
assert r.returncode==0,r.stderr
assert not REVIEW.exists()
r=subprocess.run(['rtk','proxy','git','branch','-d','codex/riverside-water-tower-v1'],cwd=ROOT,capture_output=True,text=True)
assert r.returncode==0,r.stderr
result=dict(Choice='A',BDeletedEntirely=True,DeletedAssetFiles=assets['DeletedBAssets'],DeletedFoldersAndFiles=deleted,DeletedDedicatedWorktree=str(REVIEW),OtherWorktreesPreserved=True,AKept=True)
result['DeletedDedicatedBranch']='codex/riverside-water-tower-v1'
(OUT/'deleted-b.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
