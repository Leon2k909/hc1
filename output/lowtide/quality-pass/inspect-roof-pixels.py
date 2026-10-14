from pathlib import Path
from PIL import Image
import numpy as np
root=Path(__file__).parent
for name in ('water-quay-fixed','roof-material-neutral','roof-material-charcoal','roof-material-compiled-charcoal'):
    a=np.asarray(Image.open(root/(name+'.png')).convert('RGB'))
    print(name, {str((x,y)):a[y-2:y+3,x-2:x+3].mean((0,1)).round(1).tolist() for x,y in ((800,190),(900,220),(750,180))})
