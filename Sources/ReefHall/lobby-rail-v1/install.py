"""Install the lobby balcony's new glass railing: add its 14 sections to the Reef Hall scene and take the old railing's 504
triangles out of the lobby mesh.

    python install.py --check       look at everything, change nothing
    python install.py               install (Reef Hall is brought to the front only while the scene step runs, under the
                                    editor lock; the scene that was in front goes back)
    python install.py --allow-dirty save Reef Hall even though the editor holds edits that are not in reefhall.scene

What it does, in this order:
  1. refuses unless the lobby OBJ is exactly the original or the cut (sha256) and both new models have compiled;
  2. keeps the scene as it is now in old/reefhall.scene.before (once) and checks that the editor's copy of Reef Hall holds
     nothing that is not in reefhall.scene (compared object by object, the editor's unsaved flag is not trusted);
  3. adds the scene objects "Lobby Rail N 0..6" and "Lobby Rail S 0..6" (one ModelRenderer each) under "Aquarium" and saves;
  4. swaps in stage/reefhall_lobby_without_rail.obj (the lobby without the 504 triangles; collision files are separate and
     untouched) and waits for the editor to recompile the lobby model.
revert.py undoes it. Tools/reefhall_lobby_rail.py (ENABLED) is the generator's side of the same switch.
"""
from pathlib import Path
import hashlib, json, shutil, sys, time

sys.dont_write_bytecode = True
HERE = Path(__file__).absolute().parent
sys.path.insert(0, str(HERE))
import editor as E  # noqa: E402

ROOT = E.ROOT
sys.path.insert(0, str(ROOT / 'Tools'))
SCENE = ROOT / 'Assets/scenes/maps/ReefHall/reefhall.scene'
LOBBY = ROOT / 'Assets/models/maps/reefhall/reefhall_lobby.obj'
LOBBY_VMDL = 'models/maps/reefhall/reefhall_lobby.vmdl'
ORIGINAL = HERE / 'old/reefhall_lobby_original.obj'
CUT = HERE / 'stage/reefhall_lobby_without_rail.obj'
SCENE_BEFORE = HERE / 'old/reefhall.scene.before'
PLAN = HERE / 'install-plan.json'
OBJECTS = HERE / 'native-objects.json'
FLAG = ROOT / 'Tools/reefhall_lobby_rail.py'
MODEL_DIR = ROOT / 'Assets/models/props/reefhall/lobby_rail_v1'
MODELS = ['models/props/reefhall/lobby_rail_v1/lobby_rail_section.vmdl', 'models/props/reefhall/lobby_rail_v1/lobby_rail_section_end.vmdl']
PREFIX = 'Lobby Rail '
REMOVED = 504
DUMP = E.SNIPPETS / 'reefhall_memory.json'


def sections():
    """ ( name, 'x,y,z' world position, model ) for the 14 sections, from the generator's own list (Tools/reefhall_lobby_rail.py):
    the same plan numbers, through map_kit.to_world. """
    import reefhall_lobby_rail as RL
    import map_kit as K
    count = int(round((RL.RUN_E1 - RL.RUN_E0) / RL.SECTION_LEN))
    out = []
    for tag, n in (('N', RL.RUN_N), ('S', -RL.RUN_N)):
        for j in range(count):
            e = RL.RUN_E1 - RL.SECTION_LEN / 2 - RL.SECTION_LEN * j
            x, y, z = K.to_world((e, n, RL.Z))
            out.append((f'{PREFIX}{tag} {j}', f'{x:g},{y:g},{z:g}', MODELS[1] if j == count - 1 else MODELS[0]))
    return out


CHECK = r'''var session = Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == "reefhall" );
if ( session == null ) throw new Exception( "Reef Hall is not open in the editor" );
if ( Game.IsPlaying ) throw new Exception( "A play session is running; not touching it" );
var scene = session.Scene;
System.Collections.Generic.IEnumerable<GameObject> Everything() => scene.GetAllObjects( true ).Concat( scene.GetAllObjects( false ) ).Distinct();
var aquarium = scene.Children.FirstOrDefault( g => g.Name == "Aquarium" );
var rails = Everything().Where( g => g.Name.StartsWith( "@PREFIX@" ) ).Select( g => g.Id.ToString() ).ToArray();
System.IO.File.WriteAllText( "@DUMP@", scene.Serialize().ToJsonString() );
var models = new[] { "@MODEL0@", "@MODEL1@" }.Select( Model.Load ).ToArray();
var lobby = Model.Load( "@LOBBY@" );
return new { Active = Editor.SceneEditorSession.Active?.Scene.Name, session.HasUnsavedChanges, Aquarium = aquarium?.Id.ToString(), Rails = rails,
    ModelError = models.Any( m => m.IsError ), ModelTris = models.Select( m => m.MeshInfo?.Meshes.Select( q => q.Triangles ).ToArray() ).ToArray(),
    LobbyError = lobby.IsError, LobbyTris = lobby.MeshInfo?.Meshes.Select( m => m.Triangles ).ToArray() };
'''

APPLY = r'''var session = Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == "reefhall" );
if ( session == null ) throw new Exception( "Reef Hall is not open in the editor" );
if ( Game.IsPlaying ) throw new Exception( "A play session is running; not touching it" );
if ( Editor.SceneEditorSession.Active != session ) { session.BringToFront(); await Task.Delay( 800 ); }
if ( Editor.SceneEditorSession.Active != session ) return new { Retry = true, Active = Editor.SceneEditorSession.Active?.Scene.Name, Objects = new string[0], Saved = false };
var scene = session.Scene;
System.Collections.Generic.IEnumerable<GameObject> Everything() => scene.GetAllObjects( true ).Concat( scene.GetAllObjects( false ) ).Distinct();
if ( Everything().Any( g => g.Name.StartsWith( "@PREFIX@" ) ) ) throw new Exception( "The lobby rail is already in the scene" );
var aquarium = scene.Children.FirstOrDefault( g => g.Name == "Aquarium" );
if ( aquarium == null ) throw new Exception( "No Aquarium object in the scene" );
var plan = new[] { @PLAN@ };
var ids = new System.Collections.Generic.List<string>();
foreach ( var p in plan )
{
    var model = Model.Load( p.Model );
    if ( model.IsError ) throw new Exception( "The rail model did not load: " + p.Model );
    var item = Editor.Mcp.SceneTools.CreateGameObject( name: p.Name, parent: aquarium.Id.ToString(), position: p.Position, angles: "0,0,0" );
    Editor.Mcp.SceneTools.AddComponent( item.Id.ToString(), "ModelRenderer", new System.Text.Json.Nodes.JsonObject { ["Model"] = model.ResourcePath, ["Tint"] = "1,1,1,1", ["RenderType"] = "On" } );
    ids.Add( item.Id.ToString() );
}
Editor.Mcp.SceneTools.SaveScene();
await Task.Delay( 600 );
return new { Retry = false, Active = Editor.SceneEditorSession.Active?.Scene.Name, Objects = ids.ToArray(), Saved = !session.HasUnsavedChanges };
'''

REGISTER = r'''foreach ( var p in new[] { @PATHS@ } ) Editor.AssetSystem.RegisterFile( p );
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
    own = lambda o: {k: v for k, v in o.items() if k not in ('Children', '__PrefabIdToInstanceId')}  # noqa: E731
    changed = [g for g in a if g in b and own(a[g]) != own(b[g])]
    return [g for g in a if g not in b], [g for g in b if g not in a], changed, len(a)


def prefab_map_noise(dump, scene_file):
    a = index(json.loads(Path(dump).read_text(encoding='utf-8')).get('GameObjects'), {})
    b = index(json.loads(Path(scene_file).read_text(encoding='utf-8-sig')).get('GameObjects'), {})
    return [g for g in a if g in b and a[g].get('__PrefabIdToInstanceId') != b[g].get('__PrefabIdToInstanceId')]


def scene_changes(path_a, path_b):
    """ What differs between two scene files, by object name: (only in a, only in b, objects whose own fields differ, top-level
    settings differ). The prefab id maps are left out: the editor rewrites them on every save. Other sessions edit this scene
    too, so differences from old/reefhall.scene.before are reported, not treated as errors. """
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
    count is between lo and hi and has stayed there for two looks. """
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


def compiled():
    return all((MODEL_DIR / f'{n}.vmdl_c').exists() for n in ('lobby_rail_section', 'lobby_rail_section_end'))


def main():
    args = set(sys.argv[1:])
    unknown = args - {'--check', '--allow-dirty'}
    if unknown or '--help' in args:
        raise SystemExit(__doc__)
    state = lobby_state()
    print('lobby OBJ:', state, '| new models compiled:', compiled())
    if state == 'changed':
        raise SystemExit('The lobby OBJ is neither the original nor the cut: someone changed it. Stopping.')
    if not compiled():
        raise SystemExit('The rail models have not compiled (no .vmdl_c). Compile them first.')
    scene_text = SCENE.read_text(encoding='utf-8-sig')
    has_rail = f'"{PREFIX}' in scene_text
    print('scene file names the rail:', has_rail)
    if not SCENE_BEFORE.exists():
        assert not has_rail, 'the scene already holds the rail, but there is no saved original'
        shutil.copyfile(SCENE, SCENE_BEFORE)
        print('kept the scene as it is now:', SCENE_BEFORE.relative_to(ROOT))
    plan = json.loads(PLAN.read_text()) if PLAN.exists() else {}
    plan.setdefault('scene_before', sha(SCENE_BEFORE))
    plan.setdefault('lobby_before', sha(ORIGINAL))
    plan.setdefault('lobby_after', sha(CUT))
    plan['removed_triangles'] = REMOVED
    if not has_rail and sha(SCENE) != plan['scene_before']:
        only_now, only_then, changed, top = scene_changes(SCENE, SCENE_BEFORE)
        print(f'reefhall.scene is not the saved original: {len(only_now)} objects only now, {len(only_then)} only then, '
              f'{len(changed)} with other fields {changed[:8]}, top-level settings differ: {top} '
              '(prefab id maps aside). Going on: the install only adds its own objects.', flush=True)

    code = fill(CHECK, PREFIX=PREFIX, DUMP=DUMP.as_posix(), MODEL0=MODELS[0], MODEL1=MODELS[1], LOBBY=LOBBY_VMDL)

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
        assert not check['ModelError'], 'the editor cannot load a rail model'
        assert not check['LobbyError'], 'the editor cannot load the lobby model'
        if state == 'original':
            plan['lobby_tris_before'] = sum(check['LobbyTris'] or [])
        if check['Rails']:
            print('the scene objects are already there:', len(check['Rails']))
            apply = {'Objects': check['Rails']}
        else:
            if real and '--allow-dirty' not in args:
                raise SystemExit('The editor holds scene edits that are not in reefhall.scene. Saving would take them along; '
                                 'save or discard them first, or pass --allow-dirty.')
            lines = ', '.join('new { Name = "%s", Position = "%s", Model = "%s" }' % s for s in sections())
            apply = None
            for attempt in range(8):
                apply = E.script(fill(APPLY, PREFIX=PREFIX, PLAN=lines), 'install-rail.cs')
                print(apply, flush=True)
                if not apply['Retry']:
                    break
                time.sleep(4)
            else:
                raise SystemExit('Reef Hall would not stay in front long enough; nothing was changed')
            assert apply['Saved'] and len(apply['Objects']) == 14, apply
            OBJECTS.write_text(json.dumps({'Objects': apply['Objects']}, indent=1))
    plan['scene_after'] = sha(SCENE)
    plan['objects'] = apply['Objects']
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
        print('lobby model recompiled:', before, '->', plan['lobby_tris_after'], 'compiled triangles')
    print('Installed: 14 scene objects | lobby OBJ cut | generator flag ENABLED = True')


if __name__ == '__main__':
    main()
