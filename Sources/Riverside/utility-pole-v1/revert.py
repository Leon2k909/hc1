"""Take the new utility poles back out: delete their nine scene objects and put the old dressing mesh (with the old poles) back.

    python revert.py --check          look at everything, change nothing (works with any scene in front)
    python revert.py                  revert; Riverside is brought to the front for a few seconds, then the scene that was in
                                      front goes back (the editor is shared; the lock output/editor-lock is held meanwhile)
    python revert.py --delete-assets  also delete Assets/models/props/riverside/utility_pole_v1/ and
                                      Assets/materials/riverside/utility_pole_v1/ (left in place otherwise, so install.py can
                                      put the poles back without a rebuild). The kept originals in utility_pole_original/ are
                                      never deleted.
    python revert.py --allow-dirty    save Riverside even though the editor holds edits that are not in riverside.scene

Both files are only swapped back while they are still exactly what install.py wrote (sha256), so a later edit by another
session is never overwritten. The editor's own "unsaved changes" flag on Riverside is not trusted either way: the editor's
copy of the scene is compared with riverside.scene object by object, and only real differences stop the revert.

To swap old for new without touching the mesh instead, point each pole's ModelRenderer at
models/props/riverside/utility_pole_original/pole_2arm_original.vmdl (or pole_1arm_original.vmdl) and cut nothing back in:
that draws the old shape on top of the old mesh's own, so use the full revert for that.
"""
from pathlib import Path
import hashlib, json, shutil, sys, time

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).absolute().parent))
import editor as E  # noqa: E402

OUT = E.ROOT / 'output/riverside/utility-pole-v1'
ASSET_DIRS = [E.ROOT / 'Assets/models/props/riverside/utility_pole_v1', E.ROOT / 'Assets/materials/riverside/utility_pole_v1']
SCENE = E.ROOT / 'Assets/scenes/maps/Riverside/riverside.scene'
DUMP = OUT / 'snippets/riverside_memory.json'

CODE = r'''var apply = @APPLY@;
var project = Sandbox.Project.Current.GetRootPath();
var folder = System.IO.Path.Combine( project, "output/riverside/utility-pole-v1" );
var ids = System.Text.Json.Nodes.JsonNode.Parse( System.IO.File.ReadAllText( System.IO.Path.Combine( folder, "native-objects.json" ) ) );
var groupId = Guid.Parse( ids["Group"].GetValue<string>() );
var itemIds = ids["Objects"].AsArray().Select( n => Guid.Parse( n.GetValue<string>() ) ).ToList();
var session = Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == "riverside" );
if ( session == null ) throw new Exception( "Riverside is not open in the editor" );
if ( Game.IsPlaying ) throw new Exception( "A play session is running; not touching it" );
var scene = session.Scene;
System.Collections.Generic.IEnumerable<GameObject> Everything() => scene.GetAllObjects( true ).Concat( scene.GetAllObjects( false ) );
var group = Everything().FirstOrDefault( g => g.Id == groupId );
string state = "absent";
if ( group != null )
{
	bool ok = group.Name == "Utility Poles" && group.Children.Count == itemIds.Count && group.Components.GetAll().Count() == 0;
	foreach ( var item in group.Children )
	{
		var renderer = item.Components.Get<ModelRenderer>();
		ok &= itemIds.Contains( item.Id ) && item.Name.StartsWith( "Utility Pole " ) && renderer != null && renderer.Model != null
			&& renderer.Model.ResourcePath.StartsWith( "models/props/riverside/utility_pole_v1/pole_" ) && item.Components.GetAll().Count() == 1;
	}
	if ( !ok ) throw new Exception( "The Utility Poles objects are not what install.py made; look at them in the editor first" );
	state = "installed";
}
System.IO.File.WriteAllText( "@DUMP@", scene.Serialize().ToJsonString() );
if ( apply && state == "installed" )
{
	if ( Editor.SceneEditorSession.Active != session ) throw new Exception( "Riverside is not the front document" );
	Editor.Mcp.SceneTools.DeleteGameObject( groupId.ToString() );
	Editor.Mcp.SceneTools.SaveScene();
	await Task.Delay( 300 );
	return new { State = "deleted", Gone = !Everything().Any( g => g.Id == groupId ), session.HasUnsavedChanges };
}
return new { State = state, session.HasUnsavedChanges, Front = Editor.SceneEditorSession.Active == session };
'''

REGISTER = r'''Editor.AssetSystem.RegisterFile( "@PATH@" );
return new { Registered = true };
'''

POLL = r'''var m = Model.Load( "models/maps/riverside/riverside_dressing.vmdl" );
return new { m.IsError, Tris = m.MeshInfo == null ? -1 : m.MeshInfo.Meshes.Sum( x => x.Triangles ) };
'''


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def index(objs, out):
    for o in objs or []:
        out[o['__guid']] = o
        index(o.get('Children'), out)
    return out


def differences(dump, scene_file):
    """ (objects only in the editor, only in the file, objects whose own fields differ) by __guid """
    a = index(json.loads(Path(dump).read_text(encoding='utf-8')).get('GameObjects'), {})
    b = index(json.loads(Path(scene_file).read_text(encoding='utf-8')).get('GameObjects'), {})
    own = lambda o: {k: v for k, v in o.items() if k != 'Children'}  # noqa: E731
    changed = [g for g in a if g in b and own(a[g]) != own(b[g])]
    return [g for g in a if g not in b], [g for g in b if g not in a], changed, len(a)


def run_scene_step(apply):
    code = CODE.replace('@APPLY@', 'true' if apply else 'false').replace('@DUMP@', DUMP.as_posix())
    return E.script(code, 'revert-scene.cs' if apply else 'revert-check.cs')


def main():
    args = set(sys.argv[1:])
    unknown = args - {'--check', '--delete-assets', '--allow-dirty'}
    if unknown or '--help' in args:
        raise SystemExit(__doc__)
    plan = json.loads((OUT / 'install-plan.json').read_text())
    install = json.loads((OUT / 'native-install.json').read_text())
    dressing = E.ROOT / plan['source']
    original = OUT / 'install-before/riverside_dressing.obj'
    original_tris = install['DressingTrianglesBefore']
    assert sha(original) == plan['source_before'], 'install-before/riverside_dressing.obj is not the saved original'
    assert sha(E.ROOT / 'Assets/models/maps/riverside/riverside_dressing.vmdl') == plan['dressing_vmdl'], 'The dressing ModelDoc changed since install'
    state = {plan['source_after']: 'installed', plan['source_before']: 'original'}.get(sha(dressing), 'changed')
    if state == 'changed':
        raise SystemExit('The dressing mesh is neither the installed nor the original file; someone changed it. Stopping.')

    check = run_scene_step(False)
    only_editor, only_file, changed, count = differences(DUMP, SCENE)
    real_edits = bool(only_editor or only_file or changed)
    print(f"scene objects: {check['State']}   dressing mesh: {state}   editor dirty flag: {check['HasUnsavedChanges']}")
    print(f"editor copy vs riverside.scene: {count} objects, {len(only_editor)} only in the editor, {len(only_file)} only in the file, "
          f"{len(changed)} with different fields")
    if '--check' in args:
        print('--check: nothing changed')
        return
    if check['State'] == 'installed':
        if real_edits and '--allow-dirty' not in args:
            raise SystemExit('The editor holds scene edits that are not in riverside.scene. Saving would take them along; '
                             'save or discard them first, or pass --allow-dirty.')
        with E.borrowed('riverside'):
            done = run_scene_step(True)
        print(done)
        assert done['State'] == 'deleted' and done['Gone'], done
        assert '"Utility Poles"' not in SCENE.read_text(encoding='utf-8'), 'riverside.scene still names the Utility Poles'
        # The editor re-serialises the scene when it saves, so the file need not be byte for byte the one install.py found; keep
        # its hash so install.py can put the poles back (it checks the scene against scene_before or scene_reverted).
        plan['scene_reverted'] = sha(SCENE)
        (OUT / 'install-plan.json').write_text(json.dumps(plan, indent=2))
    if state == 'installed':
        dressing.write_bytes(original.read_bytes())
        assert sha(dressing) == plan['source_before']
        print(E.script(REGISTER.replace('@PATH@', dressing.as_posix()), 'register-dressing.cs'))
        for _ in range(60):
            r = E.script(POLL, 'poll-dressing.cs')
            print(r, flush=True)
            if not r['IsError'] and r['Tris'] == original_tris:
                break
            time.sleep(3)
        else:
            raise SystemExit('The dressing has not recompiled to %d triangles yet; look at the editor' % original_tris)
    if '--delete-assets' in args:
        for folder in ASSET_DIRS:
            assert folder.resolve().parent.name == 'riverside' and folder.name == 'utility_pole_v1', folder
            if folder.exists():
                shutil.rmtree(folder)
                print('deleted', folder)
    print('Reverted: the old poles are back (dressing mesh = install-before/riverside_dressing.obj, scene without the Utility Poles objects).')


if __name__ == '__main__':
    main()
