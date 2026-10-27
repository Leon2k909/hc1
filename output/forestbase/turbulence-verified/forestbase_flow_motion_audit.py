"""Record animation evidence from timed native runtime captures without editing images."""
import argparse,hashlib,json
from datetime import datetime
from pathlib import Path
import numpy as np
from PIL import Image
import map_kit as K

REPORT=K.ROOT/'output/forestbase'
def main(prefix='flow'):
    captures=json.loads((REPORT/f'{prefix}-runtime-captures.json').read_text())
    assert len(captures)==3
    assert len({x['cameraPosition'] for x in captures})==1
    times=[datetime.fromisoformat(x['utc'].replace('Z','+00:00')) for x in captures]
    assert times[0]<times[1]<times[2]
    regions=[(711,410,730,660),(770,445,790,760),(837,480,852,720)]
    frames=[np.asarray(Image.open(REPORT/x['file']).convert('RGB'),dtype=np.int16) for x in captures]
    pairs=[]
    for index in (0,1):
        changes=[]
        for x0,y0,x1,y1 in regions:
            delta=np.abs(frames[index+1][y0:y1,x0:x1]-frames[index][y0:y1,x0:x1])
            changes.append(dict(roi=[x0,y0,x1,y1],pixelsChangedOver8=int(np.any(delta>8,axis=2).sum()),meanAbsoluteRgbDelta=float(delta.mean())))
        assert sum(x['pixelsChangedOver8'] for x in changes)>1000
        pairs.append(dict(frames=[index,index+1],elapsedSeconds=(times[index+1]-times[index]).total_seconds(),regions=changes))
    source=K.ROOT/'Assets/shaders/forestbase_waterfall.shader'
    report=dict(captures=captures,pairs=pairs,waterShaderSha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        evidenceScope='Animated appearance in three unobstructed jet regions at a fixed native runtime camera; pixel differences do not establish physical fluid simulation or independently measure the flow direction.')
    (REPORT/f'{prefix}-motion-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(pairs,indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--prefix',default='flow')
    main(parser.parse_args().prefix)
