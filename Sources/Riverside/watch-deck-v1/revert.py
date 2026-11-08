"""Take the timber watch deck back out: delete its two scene objects and put the old Pad mesh (with the old deck) back.

    python revert.py --check          look at everything, change nothing (works with any scene in front)
    python revert.py                  revert; Riverside is brought to the front for a few seconds, then the scene that was in
                                      front goes back (the editor is shared)
    python revert.py --delete-assets  also delete Assets/models/props/riverside/watch_deck_v1/ (left in place otherwise, so
                                      install.py can put the deck back without a rebuild)
    python revert.py --allow-dirty    save Riverside even though the editor holds edits that are not in riverside.scene

Both files are only swapped back while they are still exactly what install.py wrote (sha256), so a later edit by another
session is never overwritten. The editor's own "unsaved changes" flag on Riverside is not trusted either way: the editor's
copy of the scene is compared with riverside.scene object by object, and only real differences stop the revert.
"""
from pathlib import Path
import hashlib, json, shutil, sys, time

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).absolute().parent))
import editor as E  # noqa: E402

OUT = E.ROOT / 'output/riverside/watch-deck-v1'
ASSETS = E.ROOT / 'Assets/models/props/riverside/watch_deck_v1'
SCENE = E.ROOT / 'Assets/scenes/maps/Riverside/riverside.scene'
ORIGINAL_TRIS = 33152       # the Pad model's triangles with the old deck in it
DUMP = OUT / 'snippets/riverside_memory.json'

CODE = r'''var apply = @APPLY@;
var project = Sandbox.Project.Current.GetRootPath();
var folder = System.IO.Path.Combine( project, "output/riverside/watch-deck-v1" );
var ids = System.Text.Json.Nodes.JsonNode.Parse( System.IO.File.ReadAllText( System.IO.Path.Combine( folder, "native-objects.json" ) ) );
var groupId = Guid.Parse( ids["Group"].GetValue<string>() );
var itemId = Guid.Parse( ids["Object"].GetValue<string>() );
var session = Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == "riverside" );
if ( session == null ) throw new Exception( "Riverside is not open in the editor" );
if ( Game.IsPlaying ) throw new Exception( "A play session is running; not touching it" );
var scene = session.Scene;
System.Collections.Generic.IEnumerable<GameObject> Everything() => scene.GetAllObjects( true ).Concat( scene.GetAllObjects( false ) );
var group = Everything().FirstOrDefault( g => g.Id == groupId );
string state = "absent";
if ( group != null )
{
	var item = group.Children.FirstOrDefault();
	var renderer = item?.Components.Get<ModelRenderer>();
	bool ok = group.Name == "Watch Deck" && group.Children.Count == 1 && item.Id == itemId && item.Name == "Timber Watch Deck"
		&& renderer != null && renderer.Model != null && renderer.Model.ResourcePath == "models/props/riverside/watch_deck_v1/deck.vmdl"
		&& item.Components.GetAll().Count() == 1 && group.Components.GetAll().Count() == 0;
	if ( !ok ) throw new Exception( "The Watch Deck objects are not what install.py made; look at them in the editor first" );
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
return "registered";
'''

POLL = r'''var pad = Model.Load( "models/maps/riverside/riverside_pad.vmdl" );
return new { pad.IsError, Tris = pad.MeshInfo?.Meshes.Select( m => m.Triangles ).ToArray() };
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
    pad = E.ROOT / plan['source']
    original = OUT / 'install-before/riverside_pad.obj'
    assert sha(original) == plan['source_before'], 'install-before/riverside_pad.obj is not the saved original'
    assert sha(E.ROOT / 'Assets/models/maps/riverside/riverside_pad.vmdl') == plan['pad_vmdl'], 'The Pad ModelDoc changed since install'
    pad_state = {plan['source_after']: 'installed', plan['source_before']: 'original'}.get(sha(pad), 'changed')
    if pad_state == 'changed':
        raise SystemExit('The Pad mesh is neither the installed nor the original file; someone changed it. Stopping.')

    check = run_scene_step(False)
    only_editor, only_file, changed, count = differences(DUMP, SCENE)
    real_edits = bool(only_editor or only_file or changed)
    print(f"scene objects: {check['State']}   Pad mesh: {pad_state}   editor dirty flag: {check['HasUnsavedChanges']}")
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
        assert '"Watch Deck"' not in SCENE.read_text(encoding='utf-8'), 'riverside.scene still names the Watch Deck'
    if pad_state == 'installed':
        pad.write_bytes(original.read_bytes())
        assert sha(pad) == plan['source_before']
        print(E.script(REGISTER.replace('@PATH@', pad.as_posix()), 'register-pad.cs'))
        for _ in range(40):
            r = E.script(POLL, 'poll-pad.cs')
            print(r, flush=True)
            if not r['IsError'] and r['Tris'] == [ORIGINAL_TRIS]:
                break
            time.sleep(3)
        else:
            raise SystemExit('The Pad has not recompiled to %d triangles yet; look at the editor' % ORIGINAL_TRIS)
    if '--delete-assets' in args:
        assert ASSETS.resolve() == (E.ROOT / 'Assets/models/props/riverside/watch_deck_v1').resolve()
        if ASSETS.exists():
            shutil.rmtree(ASSETS)
            print('deleted', ASSETS)
    print('Reverted: the old deck is back (Pad mesh = install-before/riverside_pad.obj, scene without the Watch Deck objects).')


if __name__ == '__main__':
    main()
