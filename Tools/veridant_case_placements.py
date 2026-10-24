"""Replay only layout logic to capture precise case poses and stack RNG."""
import inspect
import json
from pathlib import Path
import map_kit as K
import veridant_map as V
import veridant_parts as P

ROOT=Path(__file__).resolve().parents[1]


class CaptureModel(K.Model):
    def __init__(self,name):super().__init__();self.name=name
    def polygon(self,*args,**kwargs):pass
    def collision_box(self,*args,**kwargs):pass
    def oriented_box(self,*args,**kwargs):pass
    def hull(self,*args,**kwargs):pass


def placements():
    rows=[];original=dict(vars(P))
    def capture(m,c,size,along=(1,0),paint='vr_case_black',z0=0.,surface='plastic',seed=0):
        rows.append({'model':m.name,'centre':list(map(float,c)),'size':list(map(float,size)),
                     'along':list(map(float,along[:2])),'paint':paint,'z0':float(z0),
                     'surface':surface,'seed':int(seed)})
    try:
        for name,value in original.items():
            if inspect.isfunction(value) and name not in ('case_stack','unit','v'):
                setattr(P,name,lambda *args,**kwargs:None)
        P.hard_case=capture
        buildings=CaptureModel('veridant_buildings');dress=CaptureModel('veridant_dress')
        glass=CaptureModel('glass');foliage=CaptureModel('foliage');pits=CaptureModel('pits')
        V.ops(buildings,glass,foliage);V.north_block(buildings,glass,foliage)
        V.courtyard(dress,foliage);V.east_terrace(buildings,glass,foliage)
        V.promenade(dress,foliage,pits);V.gardens(dress,foliage);V.forecourt(dress,foliage)
    finally:
        for name,value in original.items():setattr(P,name,value)
    return rows


if __name__=='__main__':
    rows=placements();out=ROOT/'output/veridant/cases-v3';out.mkdir(parents=True,exist_ok=True)
    (out/'placements.json').write_text(json.dumps(rows,indent=2)+'\n')
    print(json.dumps({'cases':len(rows),'by_model':{k:sum(r['model']==k for r in rows) for k in {r['model'] for r in rows}},
                      'nearest_camera':sorted(rows,key=lambda r:(r['centre'][0]+1710)**2+(r['centre'][1]+830)**2)[:4]}))
