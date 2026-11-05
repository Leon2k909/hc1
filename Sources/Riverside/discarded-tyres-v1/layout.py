import numpy as np
def placements():
 result=[]
 for base,seed,z,asset in (((-420,-260),5,96,'pad'),((-1380,860),8,0,'dressing'),((560,2330),9,0,'dressing'),((-1700,2100),10,0,'dressing')):
  rng=np.random.default_rng(seed)
  for k in range(int(rng.integers(2,4))):
   p=np.array((base[0]+rng.normal(0,12),base[1]+rng.normal(0,12),z+4.2+k*.1))
   result.append((asset,p))
 result.append(('pad',np.array((172,-110,100.2))))
 return result
