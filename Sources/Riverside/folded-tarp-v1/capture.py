from pathlib import Path
import json,hashlib
from native import call,script,OUT,ROOT
HERE=Path(__file__).parent;target='scenes/maps/riverside/riverside.scene';status=call('editor_status')
assert not status['SceneHasUnsavedChanges'],'Preserve unsaved scene edits'
existing=status['IsPlaying'];assert not existing or status['ActiveScenePath']==target,'Preserve play in another map'
scene_file=ROOT/'Assets/scenes/maps/Riverside/riverside.scene';before=hashlib.sha256(scene_file.read_bytes()).hexdigest();changed=False
try:
    if not existing:
        call('open_scene',dict(path=target));changed=True;call('play_start')
    result=script(HERE/'runtime-review.cs.txt');print(json.dumps(result,indent=2),flush=True)
    assert result['ActualPlayMode'] and not result['ErrorModels'] and result['PlayerCount']>0
finally:
    current=call('editor_status')
    if changed:
        assert current['ActiveScenePath']==target,'Scene changed externally; leave it untouched'
        if current['IsPlaying']:call('play_stop')
        call('open_scene',dict(path=status['ActiveScenePath']))
    final=call('editor_status');after=hashlib.sha256(scene_file.read_bytes()).hexdigest()
    restored=all(final[k]==status[k] for k in ('ActiveScenePath','IsPlaying','SceneHasUnsavedChanges'))
    (OUT/'state-restored.json').write_text(json.dumps(dict(restored=restored,before=status,after=final),indent=2),encoding='utf-8')
    (OUT/'scene-unchanged.json').write_text(json.dumps(dict(unchanged=before==after,before=before,after=after),indent=2),encoding='utf-8')
    assert restored and before==after
