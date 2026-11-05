from pathlib import Path
import sys,json,importlib.util
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main')
HERE=Path(__file__).parent
OUT=HERE.parents[2]/'output/riverside/ice-cabinet-v1'
spec=importlib.util.spec_from_file_location('native',ROOT/'Sources/Riverside/drinks-fridge-v1/native.py')
native=importlib.util.module_from_spec(spec);spec.loader.exec_module(native)
native.OUT=OUT
call=native.call
status=call('editor_status')
assert not status['SceneHasUnsavedChanges'],'Do not disturb an unsaved scene'
assert Path(status['Paths']['ProjectRoot']).resolve()==ROOT.resolve()
target='scenes/maps/riverside/riverside.scene'
changed=False
try:
    if status['IsPlaying']:call('play_stop')
    call('open_scene',dict(path=target));changed=True
    call('play_start')
    result=native.script(HERE/'runtime-installed.cs.txt')
    print(json.dumps(result,indent=2),flush=True)
    assert result['ActualPlayMode'] and not result['ErrorModels'] and result['PlayerCount']>0
finally:
    current=call('editor_status')
    if changed:
        assert current['ActiveScenePath']==target,'Scene changed externally; leave it untouched'
        if current['IsPlaying']:call('play_stop')
        call('open_scene',dict(path=status['ActiveScenePath']))
        if status['IsPlaying']:call('play_start')
    final=call('editor_status')
    restored=all(final[k]==status[k] for k in ('ActiveScenePath','IsPlaying','SceneHasUnsavedChanges'))
    (OUT/'installed-state-restored.json').write_text(json.dumps(dict(restored=restored,before=status,after=final),indent=2))
    assert restored
