"""Record observed native compile/capture results; never starts a compile."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/veridant/chair-v4'


def values(path):
    result=json.loads(path.read_text(encoding='utf-8'))
    return [json.loads(item['text']) for item in result['content'] if item['type']=='text']


stage=json.loads((OUT/'stage-v4/manifest.json').read_text())
for relative,row in stage['files'].items():
    with (ROOT/relative).open('rb') as stream:
        assert hashlib.file_digest(stream,'sha256').hexdigest()==row['after']
query=values(OUT/'native-resource-state/call_tools.json')
compiled=[row for row in query if 'IsCompiledAndUpToDate' in row]
assert len(compiled)==4
assert all(row['IsCompiled'] and row['IsCompiledAndUpToDate'] and not row['IsCompileFailed'] for row in compiled)
capture=values(OUT/'native-complete-views/run_csharp.json')[0]
assert capture['Stage']=='stage-v4' and not capture['ModelIsError']
assert all(capture[name] for name in ('SourceSceneUnchanged','UnsavedStateUnchanged','PlayStateUnchanged'))
report={
    'Stage':'stage-v4','Instances':stage['instances'],'TrianglesPerChair':stage['triangles_per_chair'],
    'SourceSceneUnchanged':capture['SourceSceneUnchanged'],
    'UnsavedStateUnchanged':capture['UnsavedStateUnchanged'],
    'PlayStateUnchanged':capture['PlayStateUnchanged'],
    'ModelIsError':capture['ModelIsError'],
    'Compiled':[{name:row[name] for name in ('Path','IsCompiled','IsCompiledAndUpToDate','IsCompileFailed')} for row in compiled],
    'Verification':'Fresh native resource-state inspection and capture after publication; import timed out after its source copies.',
    'Views':capture['Files'],
}
(OUT/'installed.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'Stage':'stage-v4','Instances':report['Instances'],'Compiled':len(compiled),'ModelIsError':False}))
