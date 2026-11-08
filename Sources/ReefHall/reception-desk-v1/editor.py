"""Editor helpers for the Reef Hall reception-desk trial (talks to the shared s&box editor through sbox-cli --call).

Usage (python editor.py <command> ...):  status | acquire | release | open | front <scene> | camera <scene>

The editor is shared, so: take the lock (output/editor-lock) before changing the front scene or the viewport camera,
read editor_status.ActiveScene first and put that scene back afterwards.
"""
from pathlib import Path
import json, os, shutil, subprocess, sys, time

ROOT = Path(r'C:\sbox-projects\hc1\forked-shooter-main')
ENGINE = Path(os.environ.get('FACEPUNCH_ENGINE') or r'C:\Program Files (x86)\Steam\steamapps\common\sbox')
CLI = ENGINE / 'bin/managed/sbox-cli.exe'
LOCK = ROOT / 'output/editor-lock'
OWNER = 'reefhall-model'
OUT = ROOT / 'output/model-trial-20261106/reefhall'
SCENE_NAME = 'reefhall'
SCENE_PATH = 'scenes/maps/ReefHall/reefhall.scene'


def call(tool, arguments=None, timeout=240):
    # The editor's request loop stalls for a while whenever anyone saves or compiles something big (another session, or a
    # model of mine), and sbox-cli then says "No running editor has ... open": that is transient, so look again.
    for attempt in range(12):
        r = subprocess.run([str(CLI), '--call', tool, json.dumps(arguments or {})], cwd=ROOT, capture_output=True, text=True,
                           encoding='utf-8', timeout=timeout)
        text = (r.stdout or '').strip()
        try:
            return json.loads(text)
        except ValueError:
            if r.returncode == 0 and text:
                return text
            if 'No running editor' in (text + (r.stderr or '')) and attempt < 11:
                print(f'{tool}: the editor did not answer (stalled?); looking again in 5 s', flush=True)
                time.sleep(5)
                continue
            raise RuntimeError(f'{tool}: {text} {r.stderr}'.strip())


def run(code, timeout=240):
    return call('run_csharp', {'code': code}, timeout)


def status():
    s = call('editor_status')
    assert Path(s['Paths']['ProjectRoot']).resolve() == ROOT.resolve(), s['Paths']
    return s


def sessions():
    return run('return Editor.SceneEditorSession.All.Select( x => x.Scene.Name ).ToArray();')


# ---- the editor lock -------------------------------------------------------------------------------------------

def acquire(wait=600):
    """ Takes output/editor-lock (atomic mkdir), polling every 10 s for up to `wait` seconds. A lock older than ten
    minutes is the brief's 'stale': it is reported, never taken automatically. """
    t0 = time.time()
    last = 0
    while True:
        try:
            LOCK.mkdir()
            (LOCK / 'owner.txt').write_text(OWNER + chr(10) + time.strftime('%Y-%m-%d %H:%M:%S') + chr(10))
            return True
        except FileExistsError:
            try:
                age = time.time() - LOCK.stat().st_mtime
                owner = (LOCK / 'owner.txt').read_text().strip().splitlines()[0] if (LOCK / 'owner.txt').exists() else '?'
            except OSError:
                continue
            if time.time() - last > 60:
                print(f'lock held by {owner!r}, age {age:.0f}s', flush=True)
                last = time.time()
            if age > 600:
                if os.environ.get('REEFHALL_TAKE_STALE_LOCK') == '1' and owner != OWNER:
                    # BRIEF section 6: a lock older than 10 minutes is stale. Only when asked for (and after the owner was
                    # told by message): re-read the age right before deleting, and leave a note of whose lock it was.
                    try:
                        age = time.time() - LOCK.stat().st_mtime
                    except OSError:
                        continue
                    if age > 600:
                        print(f'taking over the stale lock of {owner!r} (age {age:.0f}s)', flush=True)
                        shutil.rmtree(LOCK, ignore_errors=True)
                        try:
                            LOCK.mkdir()
                        except FileExistsError:
                            continue
                        (LOCK / 'owner.txt').write_text(OWNER + chr(10) + time.strftime('%Y-%m-%d %H:%M:%S') + chr(10)
                                                        + f'took over the stale lock of {owner} (age {age:.0f}s)' + chr(10))
                        return True
                print(f'lock older than 10 minutes ({owner!r}): not taking it automatically', flush=True)
                if time.time() - t0 > wait:
                    return False
            if time.time() - t0 > wait:
                return False
            time.sleep(1)     # the peers re-take the lock within seconds of its release: a slower poll never wins


def release():
    if LOCK.exists():
        o = LOCK / 'owner.txt'
        if o.exists() and OWNER not in o.read_text():
            print('lock is not mine; leaving it', o.read_text())
            return False
        shutil.rmtree(LOCK)
    return True


# ---- scenes and the viewport camera --------------------------------------------------------------------------------

FIND = '''
Editor.SceneEditorSession S( string name ) => Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == name );
var flags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Static | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic;
Editor.Widget Dock( Editor.SceneEditorSession s ) => (Editor.Widget) s.GetType().GetProperty( "SceneDock", flags ).GetValue( s );
Editor.Widget FindType( Editor.Widget w, string typeName )
{
    if ( w == null ) return null;
    if ( w.GetType().Name == typeName ) return w;
    foreach ( var c in w.Children ) { var f = FindType( c, typeName ); if ( f != null ) return f; }
    return null;
}
CameraComponent EditorCam( Editor.SceneEditorSession s )
{
    var vp = FindType( Dock( s ), "SceneViewportWidget" );
    return (CameraComponent) vp.GetType().GetField( "_editorCamera", flags ).GetValue( vp );
}
'''


def front(scene):
    code = FIND + f'''
var s = S( "{scene}" );
if ( s == null ) return "no session {scene}";
s.BringToFront();
await Task.Delay( 700 );
return Editor.SceneEditorSession.Active?.Scene.Name;
'''
    return run(code)


def open_scene(path=SCENE_PATH):
    return call('bridge_call', {'command': 'load_scene', 'parameters': {'path': path}}, timeout=600)


def camera(scene=None):
    """ The front scene's editor camera (native get_editor_camera). """
    return call('get_editor_camera')


def set_camera(scene, pos, ang, settle=1500):
    """ Moves the front scene's editor camera with the editor's own set_editor_camera; pos world x,y,z, ang pitch,yaw,roll. """
    r = call('set_editor_camera', {'position': '%s,%s,%s' % tuple(pos), 'angles': '%s,%s,%s' % tuple(ang)})
    time.sleep(settle / 1000.0)
    got = call('get_editor_camera')
    return {'active': status()['ActiveScene'], 'set': r, 'got': got}


def viewport_rect(scene):
    code = FIND + f'''
var s = S( "{scene}" );
var vp = FindType( Dock( s ), "SceneViewportWidget" );
var r = FindType( vp, "SceneRenderingWidget" );
return new[] {{ r.ScreenPosition.x, r.ScreenPosition.y, r.Size.x, r.Size.y }};
'''
    return run(code)


def capture(dest, rect=None):
    """ A native window capture (screenshot_game: PrintWindow of the editor) cropped to the viewport. """
    params = {}
    if rect:
        params['crop'] = {'x': rect[0], 'y': rect[1], 'w': rect[2], 'h': rect[3]}
    r = call('bridge_call', {'command': 'screenshot_game', 'parameters': params})
    assert r.get('captured'), r
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(r['path'], dest)
    return r


# ---- snippets and borrowing the scene --------------------------------------------------------------------------------

SNIPPETS = OUT / 'snippets'


def script(code, name):
    """ Runs a C# snippet in the editor process (statements ending in a return) from a file, so the editor's own compile
    errors name a line; returns what it returned. """
    SNIPPETS.mkdir(parents=True, exist_ok=True)
    path = SNIPPETS / name
    path.write_text(code, encoding='utf-8')
    return call('run_csharp', {'path': str(path)}, 300)


def ensure_open(scene=SCENE_NAME):
    if scene in sessions():
        return
    print('opening', SCENE_PATH, flush=True)
    open_scene()
    for _ in range(60):
        time.sleep(3)
        if scene in sessions():
            break
    else:
        raise RuntimeError('the scene did not open')
    time.sleep(8)


class borrowed:
    """ with borrowed(): the editor lock is held, Reef Hall is open and in front; on the way out the scene that was in front
    goes back (checked) and the lock is released. The front scene can still be flipped by another session meanwhile, so
    code inside re-checks the active scene before it changes anything. """

    def __init__(self, scene=SCENE_NAME, wait=900):
        self.scene, self.wait = scene, wait

    def __enter__(self):
        if not acquire(self.wait):
            raise SystemExit('could not get the editor lock')
        try:
            st = status()
            assert not st['IsPlaying'], 'a play session is running; not touching it'
            self.home = st['ActiveScene']
            ensure_open(self.scene)
            if status()['ActiveScene'] != self.scene:
                front(self.scene)
                time.sleep(2)
        except BaseException:
            release()
            raise
        return self.home

    def __exit__(self, *exc):
        try:
            if status()['ActiveScene'] != self.home:
                back = front(self.home)
                print('front scene restored:', back, '| expected', self.home, flush=True)
        finally:
            release()
        return False


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'status':
        print(json.dumps(status(), indent=1)); print(sessions())
    elif cmd == 'acquire':
        print(acquire())
    elif cmd == 'release':
        print(release())
    elif cmd == 'open':
        print(open_scene())
    elif cmd == 'front':
        print(front(sys.argv[2]))
    elif cmd == 'camera':
        print(camera(sys.argv[2]))
