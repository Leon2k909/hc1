"""Install Reef Hall's new curved Rotunda stairs.

    python install.py rotunda               both flights: 2 scene objects, 1,716 old triangles out of the Rotunda mesh
    python install.py <room> --check        look at everything, change nothing (no lock, no change of the front scene)
    python install.py <room> --allow-dirty  save Reef Hall even though the editor holds edits that are not in reefhall.scene

What it does, in this order:
  1. refuses unless the room's OBJ is exactly the original or the cut (sha256) and the new stair model has compiled;
  2. keeps the scene as it is now in old/reefhall.scene.before (once) and compares the editor's copy of Reef Hall with
     reefhall.scene object by object (the editor's unsaved flag is not trusted);
  3. under the editor lock, with Reef Hall in front for a few seconds: adds the scene objects (one ModelRenderer each) under
     "Aquarium" and saves; the scene that was in front goes back;
  4. swaps in stage/reefhall_<room>_without_stairs.obj (the room without the old flights' triangles; the collision files are
     separate and untouched) and waits for the editor to recompile the room model;
  5. sets the generator's flag (Tools/reefhall_stairs.py LOBBY / CONTROL) to True.
revert.py undoes it. Nothing here forces a compile: the editor recompiles a changed OBJ by itself.
"""
from pathlib import Path
import hashlib, json, re, shutil, sys, time

sys.dont_write_bytecode = True
HERE = Path(__file__).absolute().parent
sys.path.insert(0, str(HERE.parent / 'lobby-rail-v1'))
import editor as E  # noqa: E402

ROOT = E.ROOT
E.OUT = ROOT / 'output/model-trial-20261106/reefhall_rotunda_stairs'
E.SNIPPETS = E.OUT / 'snippets'
sys.path.insert(0, str(ROOT / 'Tools'))
import map_kit as K  # noqa: E402
import reefhall_stairs as RS  # noqa: E402

SCENE = ROOT / 'Assets/scenes/maps/ReefHall/reefhall.scene'
SCENE_BEFORE = HERE / 'old/reefhall.scene.before'
PLAN = HERE / 'install-plan.json'
FLAGS = ROOT / 'Tools/reefhall_stairs.py'
DUMP = E.SNIPPETS / 'reefhall_memory.json'
MODEL_DIR = ROOT / 'Assets/models/props/reefhall/stairs_v1'


def pos(e, n):
    x, y, z = K.to_world((e, n, 0.0))
    return f'{x:g},{y:g},{z:g}'


ROOMS = {
    'rotunda': dict(
        obj=ROOT / 'Assets/models/maps/reefhall/reefhall_rotunda.obj', vmdl='models/maps/reefhall/reefhall_rotunda.vmdl',
        original=HERE / 'old/reefhall_rotunda_original.obj', cut=HERE / 'stage/reefhall_rotunda_without_stairs.obj',
        removed=1716, prefix='Rotunda Stair ', flag='ROTUNDA', compiled=['rotunda_stair_ne', 'rotunda_stair_nw'],
        objects=[('Rotunda Stair NE', RS.ROTUNDA_MODELS['NE'], pos(0.0, 0.0)),
                 ('Rotunda Stair NW', RS.ROTUNDA_MODELS['NW'], pos(0.0, 0.0))]),
}


CHECK = r'''var session = Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == "reefhall" );
if ( session == null ) throw new Exception( "Reef Hall is not open in the editor" );
if ( Game.IsPlaying ) throw new Exception( "A play session is running; not touching it" );
var scene = session.Scene;
System.Collections.Generic.IEnumerable<GameObject> Everything() => scene.GetAllObjects( true ).Concat( scene.GetAllObjects( false ) ).Distinct();
var aquarium = scene.Children.FirstOrDefault( g => g.Name == "Aquarium" );
var found = Everything().Where( g => g.Name.StartsWith( "@PREFIX@" ) ).Select( g => g.Id.ToString() ).ToArray();
System.IO.File.WriteAllText( "@DUMP@", scene.Serialize().ToJsonString() );
var model = Model.Load( "@MODEL@" );
var room = Model.Load( "@ROOM@" );
return new { Active = Editor.SceneEditorSession.Active?.Scene.Name, session.HasUnsavedChanges, Aquarium = aquarium?.Id.ToString(), Found = found,
    ModelError = model.IsError, ModelTris = model.MeshInfo?.Meshes.Select( q => q.Triangles ).ToArray(),
    RoomError = room.IsError, RoomTris = room.MeshInfo?.Meshes.Select( m => m.Triangles ).ToArray() };
'''

APPLY = r'''var session = Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == "reefhall" );
if ( session == null ) throw new Exception( "Reef Hall is not open in the editor" );
if ( Game.IsPlaying ) throw new Exception( "A play session is running; not touching it" );
if ( Editor.SceneEditorSession.Active != session ) { session.BringToFront(); await Task.Delay( 800 ); }
if ( Editor.SceneEditorSession.Active != session ) return new { Retry = true, Active = Editor.SceneEditorSession.Active?.Scene.Name, Objects = new string[0], Saved = false };
var scene = session.Scene;
System.Collections.Generic.IEnumerable<GameObject> Everything() => scene.GetAllObjects( true ).Concat( scene.GetAllObjects( false ) ).Distinct();
if ( Everything().Any( g => g.Name.StartsWith( "@PREFIX@" ) ) ) throw new Exception( "These stairs are already in the scene" );
var aquarium = scene.Children.FirstOrDefault( g => g.Name == "Aquarium" );
if ( aquarium == null ) throw new Exception( "No Aquarium object in the scene" );
var plan = new[] { @PLAN@ };
var ids = new System.Collections.Generic.List<string>();
foreach ( var p in plan )
{
    var model = Model.Load( p.Model );
    if ( model.IsError ) throw new Exception( "The stair model did not load: " + p.Model );
    var item = Editor.Mcp.SceneTools.CreateGameObject( name: p.Name, parent: aquarium.Id.ToString(), position: p.Position, angles: "0,0,0" );
    Editor.Mcp.SceneTools.AddComponent( item.Id.ToString(), "ModelRenderer", new System.Text.Json.Nodes.JsonObject { ["Model"] = model.ResourcePath, ["Tint"] = "1,1,1,1", ["RenderType"] = "On" } );
    ids.Add( item.Id.ToString() );
}
Editor.Mcp.SceneTools.SaveScene();
await Task.Delay( 600 );
return new { Retry = false, Active = Editor.SceneEditorSession.Active?.Scene.Name, Objects = ids.ToArray(), Saved = !session.HasUnsavedChanges };
'''

POLL = r'''var room = Model.Load( "@ROOM@" );
return new { room.IsError, Tris = room.MeshInfo?.Meshes.Select( m => m.Triangles ).ToArray() };
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
    """ (only in the editor, only in the file, objects whose own fields differ, object count) by __guid; the prefab id maps
    are left out (the editor rewrites them on every save) """
    a = index(json.loads(Path(dump).read_text(encoding='utf-8')).get('GameObjects'), {})
    b = index(json.loads(Path(scene_file).read_text(encoding='utf-8-sig')).get('GameObjects'), {})
    own = lambda o: {k: v for k, v in o.items() if k not in ('Children', '__PrefabIdToInstanceId')}  # noqa: E731
    changed = [g for g in a if g in b and own(a[g]) != own(b[g])]
    return [g for g in a if g not in b], [g for g in b if g not in a], changed, len(a)


def scene_changes(path_a, path_b):
    """ What differs between two scene files, by object name: (only in a, only in b, objects whose own fields differ, top-level
    settings differ). Other sessions edit this scene too, so differences from old/reefhall.scene.before are reported, not
    treated as errors. """
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


def room_state(cfg):
    return {sha(cfg['original']): 'original', sha(cfg['cut']): 'cut'}.get(sha(cfg['obj']), 'changed')


def set_flag(name, on):
    text = FLAGS.read_text(encoding='utf-8')
    new = re.sub(rf'^{name} = (True|False)(?=\s*(#.*)?$)', f'{name} = {on}', text, count=1, flags=re.M)
    assert f'{name} = {on}' in new, 'could not set the generator flag'
    if new != text:
        FLAGS.write_text(new, encoding='utf-8')


def wait_for_room(cfg, lo, hi, label):
    """ The editor recompiles the room's ModelDoc by itself once it sees the OBJ change: wait until the compiled triangle
    count is between lo and hi and has stayed there for two looks. Nothing is forced. """
    code = fill(POLL, ROOM=cfg['vmdl'])
    last, steady = None, 0
    for k in range(200):
        r = E.script(code, 'poll-room.cs')
        if r != last:
            print(time.strftime('%H:%M:%S'), r, flush=True)
            last = r
        total = sum(r['Tris']) if r.get('Tris') else None
        if not r['IsError'] and total is not None and lo <= total <= hi:
            steady += 1
            if steady >= 2:
                return r
        else:
            steady = 0
        if k == 40:
            print('no recompile yet: touching the room ModelDoc (the editor can keep a stale compiled copy)', flush=True)
            import os
            os.utime(ROOT / 'Assets' / cfg['vmdl'])
        time.sleep(3)
    raise SystemExit(f'The room model has not recompiled to {lo}..{hi} triangles ({label}); look at the editor before going on')


def compiled(cfg):
    return all((MODEL_DIR / f'{n}.vmdl_c').exists() for n in cfg['compiled'])


def main():
    args = [a for a in sys.argv[1:]]
    rooms = [a for a in args if a in ROOMS]
    flags = set(args) - set(rooms)
    if len(rooms) != 1 or flags - {'--check', '--allow-dirty'} or '--help' in flags:
        raise SystemExit(__doc__)
    room = rooms[0]
    cfg = ROOMS[room]
    state = room_state(cfg)
    print(f'{room} OBJ:', state, '| new stair model compiled:', compiled(cfg))
    if state == 'changed':
        raise SystemExit('The room OBJ is neither the original nor the cut: someone changed it. Stopping.')
    if not compiled(cfg):
        raise SystemExit('The stair model has not compiled (no .vmdl_c). Compile it first.')
    scene_text = SCENE.read_text(encoding='utf-8-sig')
    has_objects = f'"{cfg["prefix"]}' in scene_text
    print('scene file names the stairs:', has_objects)
    if not SCENE_BEFORE.exists():
        assert not has_objects, 'the scene already holds the stairs, but there is no saved original'
        shutil.copyfile(SCENE, SCENE_BEFORE)
        print('kept the scene as it is now:', SCENE_BEFORE.relative_to(ROOT))
    plan = json.loads(PLAN.read_text()) if PLAN.exists() else {}
    mine = plan.setdefault(room, {})
    mine.setdefault('scene_before', sha(SCENE_BEFORE) if not has_objects else None)
    mine.setdefault('room_before', sha(cfg['original']))
    mine.setdefault('room_after', sha(cfg['cut']))
    mine['removed_triangles'] = cfg['removed']
    if not has_objects and sha(SCENE) != sha(SCENE_BEFORE):
        only_now, only_then, changed, top = scene_changes(SCENE, SCENE_BEFORE)
        print(f'reefhall.scene is not the saved original: {len(only_now)} objects only now, {len(only_then)} only then, '
              f'{len(changed)} with other fields {changed[:8]}, top-level settings differ: {top} '
              '(prefab id maps aside). Going on: the install only adds its own objects.', flush=True)

    code = fill(CHECK, PREFIX=cfg['prefix'], DUMP=DUMP.as_posix(), MODEL=cfg['objects'][0][1], ROOM=cfg['vmdl'])

    def looked():
        check = E.script(code, f'check-{room}.cs')
        print(json.dumps(check))
        only_editor, only_file, changed, count = differences(DUMP, SCENE)
        print(f'editor copy vs reefhall.scene: {count} objects, {len(only_editor)} only in the editor, {len(only_file)} only in the file, '
              f'{len(changed)} with different fields; editor dirty flag: {check["HasUnsavedChanges"]}')
        return check, bool(only_editor or only_file or changed)

    if '--check' in flags:
        looked()              # read-only: no lock, no change of the front scene
        print('--check: nothing changed')
        return
    with E.borrowed():
        check, real = looked()
        assert not check['ModelError'], 'the editor cannot load the stair model'
        assert not check['RoomError'], 'the editor cannot load the room model'
        if state == 'original':
            mine['room_tris_before'] = sum(check['RoomTris'] or [])
        if check['Found']:
            print('the scene objects are already there:', len(check['Found']))
            apply = {'Objects': check['Found']}
        else:
            if real and '--allow-dirty' not in flags:
                raise SystemExit('The editor holds scene edits that are not in reefhall.scene. Saving would take them along; '
                                 'save or discard them first, or pass --allow-dirty.')
            lines = ', '.join('new { Name = "%s", Position = "%s", Model = "%s" }' % (name, position, model)
                              for name, model, position in cfg['objects'])     # objects are ( name, model, position )
            apply = None
            for attempt in range(8):
                apply = E.script(fill(APPLY, PREFIX=cfg['prefix'], PLAN=lines), f'install-{room}.cs')
                print(apply, flush=True)
                if not apply['Retry']:
                    break
                time.sleep(4)
            else:
                raise SystemExit('Reef Hall would not stay in front long enough; nothing was changed')
            assert apply['Saved'] and len(apply['Objects']) == len(cfg['objects']), apply
    mine['scene_after'] = sha(SCENE)
    mine['objects'] = apply['Objects']
    mine.pop('reverted', None)
    PLAN.write_text(json.dumps(plan, indent=1))
    set_flag(cfg['flag'], True)

    if state == 'original':
        before = mine['room_tris_before']
        t0 = time.time()
        atomic_write(cfg['obj'], cfg['cut'].read_bytes())
        assert sha(cfg['obj']) == mine['room_after']
        print(f'swapped the {room} OBJ; waiting for the editor to recompile it (was', before, 'compiled triangles)', flush=True)
        done = wait_for_room(cfg, before - cfg['removed'], before - 1, 'install')
        mine['room_tris_after'] = sum(done['Tris'])
        mine['recompile_seconds'] = round(time.time() - t0)
        PLAN.write_text(json.dumps(plan, indent=1))
        print(f'{room} model recompiled:', before, '->', mine['room_tris_after'], f'compiled triangles in {mine["recompile_seconds"]} s')
    print(f'Installed {room}: {len(cfg["objects"])} scene object(s) | room OBJ cut | generator flag {cfg["flag"]} = True')


if __name__ == '__main__':
    main()
