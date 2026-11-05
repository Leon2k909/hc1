from pathlib import Path
import json,sys
from native import ROOT,OUT,call,script
HERE=Path(__file__).parent
status=call('editor_status');started=not status['IsPlaying']
if status['SceneHasUnsavedChanges']:raise RuntimeError('Preserve the unsaved editor scene')
if not started:raise RuntimeError('This check requires the existing stopped editor state; preserve any user play session')
try:
 if started:
  print(json.dumps(call('open_scene',dict(path='scenes/maps/railhead/railhead.scene'))),flush=True)
  result=call('play_start');print(json.dumps(result),flush=True)
 filename='runtime_review.cs.txt'
 result=script(HERE/filename);print(json.dumps(result,indent=2),flush=True)
 assert result['ActualPlayMode'] and not result['ErrorModels']
finally:
 if started:
  current=call('editor_status')
  if current['ActiveScenePath']!='scenes/maps/railhead/railhead.scene':
   raise RuntimeError('Editor changed to another scene during capture; leave the current session untouched')
  if current['IsPlaying']:print(json.dumps(call('play_stop')),flush=True)
  print(json.dumps(call('open_scene',dict(path=status['ActiveScenePath']))),flush=True)
final=call('editor_status');assert final['IsPlaying']==status['IsPlaying'] and final['ActiveScenePath']==status['ActiveScenePath'] and final['SceneHasUnsavedChanges']==status['SceneHasUnsavedChanges']
(OUT/'play-state-restored.json').write_text(json.dumps(dict(started_by_task=started,restored=True,before=status,after=final),indent=2))
