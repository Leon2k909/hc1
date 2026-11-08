"""Put Reef Hall's old straight stairs back, one room at a time (the exact opposite of install.py).

    python revert.py lobby              remove the two scene objects, restore the lobby OBJ byte for byte, flag LOBBY = False
    python revert.py control            the same for the control room's flight
    python revert.py <room> --check     look, change nothing

Under the editor lock, with Reef Hall in front for a few seconds: deletes the scene objects whose names start with the room's
prefix and saves; then restores old/reefhall_<room>_original.obj (sha256 checked against the one install.py recorded) and waits
for the editor to recompile the room model back to its old triangle count; then sets the generator's flag to False. The new
stair models stay in Assets/models/props/reefhall/stairs_v1 (nothing refers to them any more). Nothing is forced to compile.
"""
from pathlib import Path
import json, sys, time

sys.dont_write_bytecode = True
HERE = Path(__file__).absolute().parent
sys.path.insert(0, str(HERE))
import install as I  # noqa: E402  (its helpers; it also points the editor helpers at this trial's output folder)

E = I.E

DELETE = r'''var session = Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == "reefhall" );
if ( session == null ) throw new Exception( "Reef Hall is not open in the editor" );
if ( Game.IsPlaying ) throw new Exception( "A play session is running; not touching it" );
if ( Editor.SceneEditorSession.Active != session ) { session.BringToFront(); await Task.Delay( 800 ); }
if ( Editor.SceneEditorSession.Active != session ) return new { Retry = true, Active = Editor.SceneEditorSession.Active?.Scene.Name, Removed = 0, Left = -1, Saved = false };
var scene = session.Scene;
System.Collections.Generic.IEnumerable<GameObject> Everything() => scene.GetAllObjects( true ).Concat( scene.GetAllObjects( false ) ).Distinct();
var items = Everything().Where( g => g.Name.StartsWith( "@PREFIX@" ) ).ToList();
foreach ( var g in items ) Editor.Mcp.SceneTools.DeleteGameObject( g.Id.ToString() );
Editor.Mcp.SceneTools.SaveScene();
await Task.Delay( 600 );
return new { Retry = false, Active = Editor.SceneEditorSession.Active?.Scene.Name, Removed = items.Count, Left = Everything().Count( g => g.Name.StartsWith( "@PREFIX@" ) ), Saved = !session.HasUnsavedChanges };
'''


def main():
    args = sys.argv[1:]
    rooms = [a for a in args if a in I.ROOMS]
    flags = set(args) - set(rooms)
    if len(rooms) != 1 or flags - {'--check'}:
        raise SystemExit(__doc__)
    room = rooms[0]
    cfg = I.ROOMS[room]
    plan = json.loads(I.PLAN.read_text()) if I.PLAN.exists() else {}
    mine = plan.get(room, {})
    state = I.room_state(cfg)
    scene_text = I.SCENE.read_text(encoding='utf-8-sig')
    print(f'{room} OBJ:', state, '| scene file names the stairs:', f'"{cfg["prefix"]}' in scene_text)
    if state == 'changed':
        raise SystemExit('The room OBJ is neither the original nor the cut: someone changed it. Stopping.')
    if '--check' in flags:
        print('--check: nothing changed')
        return
    with E.borrowed():
        for attempt in range(8):
            done = E.script(I.fill(DELETE, PREFIX=cfg['prefix']), f'revert-{room}.cs')
            print(done, flush=True)
            if not done['Retry']:
                break
            time.sleep(4)
        else:
            raise SystemExit('Reef Hall would not stay in front long enough; nothing was changed')
        assert done['Left'] == 0 and done['Saved'], done
    if state == 'cut':
        now = E.script(I.fill(I.POLL, ROOM=cfg['vmdl']), 'poll-room.cs')
        print('room model now:', now, flush=True)
        t0 = time.time()
        I.atomic_write(cfg['obj'], cfg['original'].read_bytes())
        assert I.sha(cfg['obj']) == I.sha(cfg['original'])
        before = sum(now['Tris'])
        want = mine.get('room_tris_before')
        lo, hi = (want, want) if want else (before + 1, before + cfg['removed'])
        print(f'restored the original {room} OBJ; waiting for the editor to recompile it to', want or f'{lo}..{hi}', flush=True)
        r = I.wait_for_room(cfg, lo, hi, 'revert')
        print(f'{room} model recompiled:', sum(r['Tris']), f'compiled triangles in {round(time.time() - t0)} s')
    I.set_flag(cfg['flag'], False)
    mine['reverted'] = True
    plan[room] = mine
    I.PLAN.write_text(json.dumps(plan, indent=1))
    print(f'Reverted {room}: scene objects removed | room OBJ is the original again | generator flag {cfg["flag"]} = False')


if __name__ == '__main__':
    main()
