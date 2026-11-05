from pathlib import Path
import json,hashlib
from native import call,script,OUT,ROOT
HERE=Path(__file__).parent
status=call('editor_status')
scene_file=ROOT/'Assets/scenes/maps/Riverside/riverside.scene'
scene_before=hashlib.sha256(scene_file.read_bytes()).hexdigest()
assert not status['SceneHasUnsavedChanges'],'Preserve unsaved scenes'
target='scenes/maps/riverside/riverside.scene'
assert not status['IsPlaying'],'Preserve an existing play session during the preview'
changed=False
try:
    call('open_scene',dict(path=target));changed=True
    call('play_start')
    result=script(HERE/'runtime-lighting.cs.txt')
    print(json.dumps(result,indent=2),flush=True)
    assert result['ActualPlayMode'] and not result['ErrorModels'] and result['PlayerCount']>0
finally:
    current=call('editor_status')
    if changed:
        assert current['ActiveScenePath']==target,'Scene changed externally; leave it untouched'
        if current['IsPlaying']:call('play_stop')
        call('open_scene',dict(path=status['ActiveScenePath']))
    final=call('editor_status')
    scene_after=hashlib.sha256(scene_file.read_bytes()).hexdigest()
    (OUT/'lighting-saved-scene.json').write_text(json.dumps(dict(before=scene_before,after=scene_after,unchanged=scene_before==scene_after),indent=2),encoding='utf-8')
    restored=all(final[k]==status[k] for k in ('ActiveScenePath','IsPlaying','SceneHasUnsavedChanges'))
    (OUT/'lighting-state-restored.json').write_text(json.dumps(dict(restored=restored,before=status,after=final),indent=2))
    assert restored
