"""Finish the task-owned play check after the transient CLI discovery failure."""
import json
from pathlib import Path
from native import OUT,call,script
HERE=Path(__file__).parent
status=json.loads((OUT/'play-state-restored.json').read_text())['before']
current=call('editor_status')
assert status['ActiveScenePath']==current['ActiveScenePath']=='scenes/maps/riverside/riverside.scene'
assert not status['IsPlaying'] and current['IsPlaying'] and not current['SceneHasUnsavedChanges']
try:
 result=script(HERE/'runtime_review.cs.txt');print(json.dumps(result,indent=2),flush=True)
 assert result['ActualPlayMode'] and result['PlayerCount']>0 and not result['ErrorModels']
finally:
 current=call('editor_status')
 if current['ActiveScenePath']!='scenes/maps/riverside/riverside.scene':
  raise RuntimeError('Another editor user changed scene; leave it untouched')
 if current['IsPlaying']:print(json.dumps(call('play_stop')),flush=True)
 print(json.dumps(call('open_scene',dict(path=status['ActiveScenePath']))),flush=True)
final=call('editor_status')
for field in ('ActiveScenePath','IsPlaying','SceneHasUnsavedChanges'):assert final[field]==status[field]
(OUT/'play-state-restored.json').write_text(json.dumps(dict(started_by_task=True,restored=True,before=status,after=final),indent=2))
