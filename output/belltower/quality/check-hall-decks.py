"""Verify visible decks respect the original slab and stair openings."""
from pathlib import Path
import json
import sys
import numpy as np

root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'Tools'))
import belltower_interiors as I
from belltower_map import Place
from map_kit import Model

holes=[(-434,-374,760,991),(374,434,760,991)]
results=[]
for underside,z in ((False,168),(True,340)):
    model=Model()
    I.deck(model,Place((0,0,0)),-434,434,566,1084,z,() if underside else holes,underside)
    points=np.array([p for items in model.polygons.values() for polygon,_ in items for p in polygon])
    assert np.isfinite(points).all()
    assert (points[:,0]>=-434).all() and (points[:,0]<=434).all()
    assert (points[:,1]>=566).all() and (points[:,1]<=1084).all()
    assert (points[:,2]>=(z if underside else z-1)).all()
    assert (points[:,2]<=(z+1 if underside else z)).all()
    if not underside:
        for a,b,c,d in holes:
            assert not ((points[:,0]>a)&(points[:,0]<b)&(points[:,1]>c)&(points[:,1]<d)).any()
    assert not model.boxes and not model.hulls
    results.append({'surface':'ceiling' if underside else 'floor','triangles':model.triangle_count(),
                    'finite':True,'inside_original_slab':True,'stairwells_clear':True,'collision_added':False})
(root/'output/belltower/quality/hall-v2-deck-checks.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
