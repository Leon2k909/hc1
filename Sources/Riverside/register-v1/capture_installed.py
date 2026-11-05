from pathlib import Path
import json
from native import call,script,OUT
HERE=Path(__file__).parent
status=call('editor_status')
assert not status['SceneHasUnsavedChanges'],'Preserve unsaved scenes'
target='scenes/maps/riverside/riverside.scene'
assert not status['IsPlaying'],'Preserve an existing play session during the preview'
changed=False
try:
    call('open_scene',dict(path=target));changed=True
    call('play_start')
    result=script(HERE/'runtime-installed.cs.txt')
    print(json.dumps(result,indent=2),flush=True)
    assert result['ActualPlayMode'] and not result['ErrorModels'] and result['PlayerCount']>0
finally:
    current=call('editor_status')
    if changed:
        assert current['ActiveScenePath']==target,'Scene changed externally; leave it untouched'
        if current['IsPlaying']:call('play_stop')
        call('open_scene',dict(path=status['ActiveScenePath']))
    final=call('editor_status')
    restored=all(final[k]==status[k] for k in ('ActiveScenePath','IsPlaying','SceneHasUnsavedChanges'))
    (OUT/'installed-state-restored.json').write_text(json.dumps(dict(restored=restored,before=status,after=final),indent=2))
    assert restored
