"""Install the lobby reception desk: add it to the Reef Hall scene and take the old desk's 204 triangles out of the lobby mesh.

    python install.py --check       look at everything, change nothing
    python install.py               install (Reef Hall is brought to the front only while the scene step runs, under the
                                    editor lock; the scene that was in front goes back)
    python install.py --allow-dirty save Reef Hall even though the editor holds edits that are not in reefhall.scene

What it does, in this order:
  1. refuses unless the lobby OBJ is exactly the original or the cut (sha256) and the new model has compiled;
  2. keeps the scene as it is now in old/reefhall.scene.before (once) and checks that the editor's copy of Reef Hall holds
     nothing that is not in reefhall.scene (compared object by object, the editor's unsaved flag is not trusted);
  3. adds the scene object "Lobby Reception Desk" (one ModelRenderer) under "Aquarium" at world (0, 2420, 0) and saves;
  4. swaps in stage/reefhall_lobby_without_desk.obj (the lobby without the 204 triangles; collision files are separate and
     untouched) and waits for the editor to recompile the lobby model.
revert.py undoes it. Tools/reefhall_reception_desk.py (ENABLED) is the generator's side of the same switch.
"""
from pathlib import Path
import hashlib, json, shutil, sys, time

sys.dont_write_bytecode = True
HERE = Path(__file__).absolute().parent
sys.path.insert(0, str(HERE))
import editor as E  # noqa: E402

ROOT = E.ROOT
SCENE = ROOT / 'Assets/scenes/maps/ReefHall/reefhall.scene'
LOBBY = ROOT / 'Assets/models/maps/reefhall/reefhall_lobby.obj'
LOBBY_VMDL = 'models/maps/reefhall/reefhall_lobby.vmdl'
ORIGINAL = HERE / 'old/reefhall_lobby_original.obj'
CUT = HERE / 'stage/reefhall_lobby_without_desk.obj'
SCENE_BEFORE = HERE / 'old/reefhall.scene.before'
PLAN = HERE / 'install-plan.json'
OBJECTS = HERE / 'native-objects.json'
FLAG = ROOT / 'Tools/reefhall_reception_desk.py'
MODEL = 'models/props/reefhall/reception_desk_v1/reception_desk.vmdl'
MODEL_C = ROOT / 'Assets/models/props/reefhall/reception_desk_v1/reception_desk.vmdl_c'
NAME = 'Lobby Reception Desk'
REMOVED = 204
DUMP = E.SNIPPETS / 'reefhall_memory.json'

CHECK = r'''var session = Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == "reefhall" );
if ( session == null ) throw new Exception( "Reef Hall is not open in the editor" );
if ( Game.IsPlaying ) throw new Exception( "A play session is running; not touching it" );
var scene = session.Scene;
System.Collections.Generic.IEnumerable<GameObject> Everything() => scene.GetAllObjects( true ).Concat( scene.GetAllObjects( false ) ).Distinct();
var aquarium = scene.Children.FirstOrDefault( g => g.Name == "Aquarium" );
var desks = Everything().Where( g => g.Name == "@NAME@" ).Select( g => g.Id.ToString() ).ToArray();
System.IO.File.WriteAllText( "@DUMP@", scene.Serialize().ToJsonString() );
var model = Model.Load( "@MODEL@" );
var lobby = Model.Load( "@LOBBY@" );
return new { Active = Editor.SceneEditorSession.Active?.Scene.Name, session.HasUnsavedChanges, Aquarium = aquarium?.Id.ToString(), Desks = desks,
    ModelError = model.IsError, ModelTris = model.MeshInfo?.Meshes.Select( m => m.Triangles ).ToArray(),
    LobbyError = lobby.IsError, LobbyTris = lobby.MeshInfo?.Meshes.Select( m => m.Triangles ).ToArray() };
'''

APPLY = r'''var session = Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == "reefhall" );
if ( session == null ) throw new Exception( "Reef Hall is not open in the editor" );
if ( Game.IsPlaying ) throw new Exception( "A play session is running; not touching it" );
if ( Editor.SceneEditorSession.Active != session ) { session.BringToFront(); await Task.Delay( 800 ); }
if ( Editor.SceneEditorSession.Active != session ) return new { Retry = true, Active = Editor.SceneEditorSession.Active?.Scene.Name, Object = "" };
var scene = session.Scene;
System.Collections.Generic.IEnumerable<GameObject> Everything() => scene.GetAllObjects( true ).Concat( scene.GetAllObjects( false ) ).Distinct();
if ( Everything().Any( g => g.Name == "@NAME@" ) ) throw new Exception( "The reception desk is already in the scene" );
var model = Model.Load( "@MODEL@" );
if ( model.IsError ) throw new Exception( "The reception desk model did not load" );
var aquarium = scene.Children.FirstOrDefault( g => g.Name == "Aquarium" );
if ( aquarium == null ) throw new Exception( "No Aquarium object in the scene" );
var item = Editor.Mcp.SceneTools.CreateGameObject( name: "@NAME@", parent: aquarium.Id.ToString(), position: "0,2420,0", angles: "0,0,0" );
Editor.Mcp.SceneTools.AddComponent( item.Id.ToString(), "ModelRenderer", new System.Text.Json.Nodes.JsonObject { ["Model"] = model.ResourcePath, ["Tint"] = "1,1,1,1", ["RenderType"] = "On" } );
Editor.Mcp.SceneTools.SaveScene();
await Task.Delay( 400 );
return new { Retry = false, Active = Editor.SceneEditorSession.Active?.Scene.Name, Object = item.Id.ToString(), Saved = !session.HasUnsavedChanges };
'''

REGISTER = r'''Editor.AssetSystem.RegisterFile( "@PATH@" );
return "registered";
'''

POLL = r'''var lobby = Model.Load( "@LOBBY@" );
return new { lobby.IsError, Tris = lobby.MeshInfo?.Meshes.Select( m => m.Triangles ).ToArray() };
'''


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def fill(code, **kw):
    for k, v in kw.items():
        code = code.replace('@' + k + '@', str(v))
    return code


def index(objs, out):
    for o in objs or []:
        out[o['__guid']] = o
        index(o.get('Children'), out)
    return out


def differences(dump, scene_file):
    """ (only in the editor, only in the file, objects whose own fields differ, object count) by __guid """
    a = index(json.loads(Path(dump).read_text(encoding='utf-8')).get('GameObjects'), {})
    b = index(json.loads(Path(scene_file).read_text(encoding='utf-8-sig')).get('GameObjects'), {})
    # __PrefabIdToInstanceId is left out: the editor re-derives one id pair in two prefab instances' maps whenever it saves
    # (Riverside's watch-deck README says the same); it is counted separately by prefab_map_noise.
    own = lambda o: {k: v for k, v in o.items() if k not in ('Children', '__PrefabIdToInstanceId')}  # noqa: E731
    changed = [g for g in a if g in b and own(a[g]) != own(b[g])]
    return [g for g in a if g not in b], [g for g in b if g not in a], changed, len(a)


def prefab_map_noise(dump, scene_file):
    """ The prefab instances whose __PrefabIdToInstanceId map differs between the editor's copy and the file. """
    a = index(json.loads(Path(dump).read_text(encoding='utf-8')).get('GameObjects'), {})
    b = index(json.loads(Path(scene_file).read_text(encoding='utf-8-sig')).get('GameObjects'), {})
    return [g for g in a if g in b and a[g].get('__PrefabIdToInstanceId') != b[g].get('__PrefabIdToInstanceId')]


def scene_changes(path_a, path_b):
    """ What differs between two scene files, by object name: (only in a, only in b, objects whose own fields differ, top-level
    settings differ). The prefab instances' __PrefabIdToInstanceId maps are left out: the editor rewrites them on every save,
    so a scene that went through install and revert is not byte-identical to the original although nothing real differs.
    Other sessions edit this scene too, so differences from old/reefhall.scene.before are reported, not treated as errors. """
    a, b = (json.loads(Path(p).read_text(encoding='utf-8-sig')) for p in (path_a, path_b))
    top = lambda s: {k: v for k, v in s.items() if k != 'GameObjects'}  # noqa: E731
    own = lambda o: {k: v for k, v in o.items() if k not in ('Children', '__PrefabIdToInstanceId')}  # noqa: E731
    ia, ib = index(a.get('GameObjects'), {}), index(b.get('GameObjects'), {})
    return ([ia[g].get('Name') for g in ia if g not in ib], [ib[g].get('Name') for g in ib if g not in ia],
            [ia[g].get('Name') for g in ia if g in ib and own(ia[g]) != own(ib[g])], top(a) != top(b))


def atomic_write(path, data):
    """ Writes beside the file and renames over it, as map_kit.write_text does: the editor never reads half a file. """
    temp = path.with_name(path.name + '.writing')
    temp.write_bytes(data)
    for attempt in range(40):
        try:
            temp.replace(path)
            return
        except PermissionError:
            if attempt == 39:
                raise
            time.sleep(0.5)


def lobby_state():
    return {sha(ORIGINAL): 'original', sha(CUT): 'cut'}.get(sha(LOBBY), 'changed')


def set_flag(on):
    text = FLAG.read_text(encoding='utf-8')
    new = text.replace('ENABLED = ' + ('False' if on else 'True'), 'ENABLED = ' + ('True' if on else 'False'), 1)
    assert 'ENABLED = ' + ('True' if on else 'False') in new, 'could not set the generator flag'
    if new != text:
        FLAG.write_text(new, encoding='utf-8')


def wait_for_lobby(lo, hi, label):
    """ The editor recompiles the lobby ModelDoc by itself once it sees the OBJ change: wait until the compiled triangle
    count is between lo and hi and has stayed there for two looks. (The compiler keeps fewer triangles than the OBJ holds:
    42,533 of 43,258 before the install, so the drop for the desk is read off, not assumed to be exactly 204.) """
    code = fill(POLL, LOBBY=LOBBY_VMDL)
    last, steady = None, 0
    for k in range(120):
        r = E.script(code, 'poll-lobby.cs')
        if r != last:
            print(r, flush=True)
            last = r
        total = sum(r['Tris']) if r.get('Tris') else None
        if not r['IsError'] and total is not None and lo <= total <= hi:
            steady += 1
            if steady >= 2:
                return r
        else:
            steady = 0
        if k == 25:
            print('no recompile yet: touching the lobby ModelDoc (the editor can keep a stale compiled copy)', flush=True)
            import os
            os.utime(ROOT / 'Assets' / LOBBY_VMDL)
        time.sleep(3)
    raise SystemExit(f'The lobby model has not recompiled to {lo}..{hi} triangles ({label}); look at the editor before going on')


def main():
    args = set(sys.argv[1:])
    unknown = args - {'--check', '--allow-dirty'}
    if unknown or '--help' in args:
        raise SystemExit(__doc__)
    state = lobby_state()
    print('lobby OBJ:', state, '| new model compiled:', MODEL_C.exists())
    if state == 'changed':
        raise SystemExit('The lobby OBJ is neither the original nor the cut: someone changed it. Stopping.')
    if not MODEL_C.exists():
        raise SystemExit('The reception desk model has not compiled (no reception_desk.vmdl_c). Compile it first.')
    scene_text = SCENE.read_text(encoding='utf-8-sig')
    has_desk = f'"{NAME}"' in scene_text
    print('scene file names the desk:', has_desk)
    if not SCENE_BEFORE.exists():
        assert not has_desk, 'the scene already holds the desk, but there is no saved original'
        shutil.copyfile(SCENE, SCENE_BEFORE)
        print('kept the scene as it is now:', SCENE_BEFORE.relative_to(ROOT))
    plan = json.loads(PLAN.read_text()) if PLAN.exists() else {}
    plan.setdefault('scene_before', sha(SCENE_BEFORE))
    plan.setdefault('lobby_before', sha(ORIGINAL))
    plan.setdefault('lobby_after', sha(CUT))
    plan['removed_triangles'] = REMOVED
    if not has_desk and sha(SCENE) != plan['scene_before']:
        # Not the scene as it was when the original was kept: another session may have edited it since (on 2026-11-06 the
        # Rotunda's model and Rotunda Bench 1's position changed at 19:05). The install only adds its own object to the
        # editor's open copy, and the editor-vs-file check below stops it if the editor holds anything unsaved, so go on.
        only_now, only_then, changed, top = scene_changes(SCENE, SCENE_BEFORE)
        print(f'reefhall.scene is not the saved original: {len(only_now)} objects only now, {len(only_then)} only then, '
              f'{len(changed)} with other fields {changed[:8]}, top-level settings differ: {top} '
              '(prefab id maps aside). Going on: the install only adds its own object.', flush=True)

    code = fill(CHECK, NAME=NAME, DUMP=DUMP.as_posix(), MODEL=MODEL, LOBBY=LOBBY_VMDL)

    def looked():
        check = E.script(code, 'check-reefhall.cs')
        print(json.dumps(check))
        only_editor, only_file, changed, count = differences(DUMP, SCENE)
        print(f'editor copy vs reefhall.scene: {count} objects, {len(only_editor)} only in the editor, {len(only_file)} only in the file, '
              f'{len(changed)} with different fields (prefab id maps aside: {len(prefab_map_noise(DUMP, SCENE))}); '
              f'editor dirty flag: {check["HasUnsavedChanges"]}')
        return check, bool(only_editor or only_file or changed)

    if '--check' in args:
        looked()              # read-only: no lock, no change of the front scene
        print('--check: nothing changed')
        return
    with E.borrowed():
        check, real = looked()
        assert not check['ModelError'], 'the editor cannot load the reception desk model'
        assert not check['LobbyError'], 'the editor cannot load the lobby model'
        plan['lobby_tris_before'] = sum(check['LobbyTris'] or [])
        if check['Desks']:
            print('the scene object is already there:', check['Desks'])
            apply = {'Object': check['Desks'][0]}
        else:
            if real and '--allow-dirty' not in args:
                raise SystemExit('The editor holds scene edits that are not in reefhall.scene. Saving would take them along; '
                                 'save or discard them first, or pass --allow-dirty.')
            apply = None
            for attempt in range(8):
                apply = E.script(fill(APPLY, NAME=NAME, MODEL=MODEL), 'install-desk.cs')
                print(apply, flush=True)
                if not apply['Retry']:
                    break
                time.sleep(4)
            else:
                raise SystemExit('Reef Hall would not stay in front long enough; nothing was changed')
            assert apply['Saved'], apply
            OBJECTS.write_text(json.dumps({'Object': apply['Object']}, indent=1))
    plan['scene_after'] = sha(SCENE)
    plan['object'] = apply['Object']
    PLAN.write_text(json.dumps(plan, indent=1))
    set_flag(True)

    if state == 'original':
        before = plan['lobby_tris_before']
        atomic_write(LOBBY, CUT.read_bytes())
        assert sha(LOBBY) == plan['lobby_after']
        print('swapped the lobby OBJ; waiting for the editor to recompile it (was', before, 'compiled triangles)', flush=True)
        done = wait_for_lobby(before - REMOVED, before - 1, 'install')
        plan['lobby_tris_after'] = sum(done['Tris'])
        PLAN.write_text(json.dumps(plan, indent=1))
        print('lobby model recompiled:', before, '->', plan['lobby_tris_after'], 'triangles (OBJ faces 43258 -> 43054)')
    print('Installed: scene object', plan['object'], '| lobby OBJ cut | generator flag ENABLED = True')


if __name__ == '__main__':
    main()
