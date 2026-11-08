"""Small helpers for talking to the shared s&box editor from install.py and revert.py.

Calls go through `sbox-cli --call <tool> <json>` (the editor's own MCP front door). The editor is shared with other
sessions (see output/model-trial-20261106/BRIEF.md), so a scene is only ever brought to the front for as long as a step needs
it, under the shared lock directory output/editor-lock (mkdir is the atomic take), and `borrowed()` always puts the scene that
was in front back, checking the editor reports it again.
"""
from contextlib import contextmanager
from pathlib import Path
import datetime, json, os, shutil, subprocess, time

ROOT = Path(__file__).absolute().parents[3]
ENGINE = Path(os.environ.get('FACEPUNCH_ENGINE') or r'C:\Program Files (x86)\Steam\steamapps\common\sbox')
CLI = ENGINE / 'bin/managed/sbox-cli.exe'
SNIPPETS = ROOT / 'output/riverside/utility-pole-v1/snippets'
LOCK = ROOT / 'output/editor-lock'
OWNER = 'Riverside utility-pole-v1 install/revert (3D map model improvements, Riverside session)'


def call(tool, arguments=None, timeout=240):
    r = subprocess.run([str(CLI), '--call', tool, json.dumps(arguments or {})], cwd=ROOT, capture_output=True, text=True,
                       encoding='utf-8', timeout=timeout)
    text = (r.stdout or '').strip()
    try:
        return json.loads(text)
    except ValueError:
        raise RuntimeError(f'{tool}: {text} {r.stderr}'.strip())


def script(code, name):
    """ Run a C# snippet in the editor process (statements, ending in a return) and return what it returned. """
    SNIPPETS.mkdir(parents=True, exist_ok=True)
    path = SNIPPETS / name
    path.write_text(code, encoding='utf-8')
    return call('run_csharp', dict(path=str(path)))


FRONT = '''var s = Editor.SceneEditorSession.All.First( x => x.Scene.Name == "{scene}" );
var before = Editor.SceneEditorSession.Active?.Scene.Name;
s.BringToFront();
await Task.Delay( 800 );
return new {{ before, after = Editor.SceneEditorSession.Active?.Scene.Name }};
'''


def front(scene):
    r = script(FRONT.format(scene=scene), f'front-{scene}.cs')
    assert r['after'] == scene, r
    return r


@contextmanager
def locked(wait=600):
    """ The shared editor lock: mkdir is atomic. A lock older than 10 minutes is reported, never taken over. """
    deadline = time.time() + wait
    while True:
        try:
            LOCK.mkdir()
            break
        except FileExistsError:
            age = time.time() - LOCK.stat().st_mtime
            owner = (LOCK / 'owner.txt').read_text().splitlines()[0] if (LOCK / 'owner.txt').exists() else '?'
            if age > 600:
                raise SystemExit(f'The editor lock is stale ({age:.0f} s old, held by {owner}); not taking it over. Look at it first.')
            if time.time() > deadline:
                raise SystemExit(f'The editor lock stayed busy ({owner}).')
            time.sleep(2)
    (LOCK / 'owner.txt').write_text(OWNER + '\n' + datetime.datetime.now().astimezone().isoformat(timespec='seconds') + '\n')
    try:
        yield
    finally:
        try:
            (LOCK / 'owner.txt').unlink()
        finally:
            LOCK.rmdir()


@contextmanager
def borrowed(scene):
    """ Take the lock, bring `scene` to the front, give back the one that was there (reported by editor_status) """
    with locked():
        status = call('editor_status')
        assert Path(status['Paths']['ProjectRoot']).resolve() == ROOT.resolve(), status['Paths']
        assert not status['IsPlaying'], 'A play session is running; not touching it'
        home = status['ActiveScene']
        if home == scene:
            yield status
            return
        front(scene)
        try:
            yield status
        finally:
            r = front(home)
            assert call('editor_status')['ActiveScene'] == home, r
