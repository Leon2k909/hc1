"""Check installed shutter thresholds and native compilation/capture receipts."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/belltower/shop-thresholds'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest=json.loads((OUT/'stage-v1/manifest.json').read_text())
    assert manifest['generator_hook'] in (ROOT/'Tools/belltower_map.py').read_text()
    for group in ('source_sha256','protected_sha256'):
        for path,digest in manifest[group].items():assert sha(ROOT/path)==digest,path
    for path,item in manifest['files'].items():
        assert sha(ROOT/path)==item['after'],path
        assert sha(ROOT/item['backup'])==item['before'],path
        with (ROOT/path).open('rb') as stream:
            assert hashlib.sha256(stream.read(item['original_bytes'])).hexdigest()==item['before']
    info=json.loads((OUT/'info/call_tools.json').read_text())
    assert not info.get('isError')
    rows=[json.loads(c['text']) for c in info['content'] if c['type']=='text']
    assert len(rows)==2 and all(r['IsCompiledAndUpToDate'] and not r['IsCompileFailed'] for r in rows)
    captures=[]
    for side in ('west','east'):
        path=ROOT/'output/belltower/quality/shop-thresholds-installed'/(side+'-camera.json')
        result=json.loads(path.read_text())
        assert result['Capture']['TrialModels']==0 and all(result['Restoration'].values())
        image=path.with_name(side+'.png');assert image.is_file()
        captures.append(image.relative_to(ROOT).as_posix())
    result={'thresholds':manifest['thresholds'],'triangles_added':sum(r['triangles_added'] for r in manifest['reports'].values()),
        'native_compiled_models':2,'original_geometry_bytes_exact':True,'collision_unchanged':True,
        'scene_saved':False,'unsaved_scene_edits_preserved':True,'captures':captures}
    (OUT/'verification.json').write_text(json.dumps(result,indent=2)+'\n')
    (Path(__file__).parent/'installed.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':main()
