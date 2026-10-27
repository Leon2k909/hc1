from pathlib import Path
import json
out=Path(__file__).resolve().parent
raw=json.loads((out/'info-final-preview/call_tools.json').read_text())
rows=[json.loads(c['text']) for c in raw['content'] if c['type']=='text']
assert len(rows)==7 and all(r['IsCompiledAndUpToDate'] and not r['IsCompileFailed'] for r in rows)
request=json.loads((out/'import-request.json').read_text());assert request['stage']=='stage-v5'
request['preview']=False;(out/'import-request.json').write_text(json.dumps(request))
print('Verified all preview resources; prepared live pipe-only publication')
