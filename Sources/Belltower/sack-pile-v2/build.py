from pathlib import Path
from collections import Counter
import importlib.util,json,math,re,sys,tempfile
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,belltower_map as B,belltower_detail as D,belltower_furniture as F
from belltower_move_square_lamps import geometry,sha
spec=importlib.util.spec_from_file_location('lantern',ROOT/'Sources/Belltower/wall-lantern-v2/build.py');L=importlib.util.module_from_spec(spec);spec.loader.exec_module(L)
OUT=Path(tempfile.gettempdir())/'belltower-sack-pile-v2';STAGE=OUT/'stage';RES='models/maps/belltower/sack-pile-v2';MODEL=STAGE/'Assets'/RES
HOOK=(-1215.,730.,0.)
MAPS={'canvas_plain':'materials/buildings/canvas_plain.vmat'}

def build(lod):
    m=K.Model()
    for k in range(7):
        row,level=k%3,k//3
        centre=np.array((row*22-12+level*6.,0.,level*14+7.))
        # Rounded stuffed canvas, with pinched sides and weight-bearing flat contact areas.
        part=K.Model();p=B.Place((0,0,0),0)
        F.sack(part,p,centre,size=(20,28,14),seed=k+3)
        # Simplify source surface tessellation only in the far LOD by skipping separate seam hardware.
        for paint,faces in part.polygons.items():
            for i,(points,normal) in enumerate(faces):
                m.polygon(paint,points,normal,uv=part.polygon_uvs.get((paint,i)),normals=part.polygon_normals.get((paint,i)))
        if lod<2:
            # Rolled end seam and paired rows of stitches at the sewn mouth.
            points=[centre+np.array((x,12.2,1.2-.018*x*x)) for x in np.linspace(-7.4,7.4,17)]
            L.C.tube(m,points,.15,'canvas_plain',sides=6)
            if lod==0:
                for x in np.linspace(-6.8,6.8,15):
                    q=centre+np.array((x,12.35,1.25-.018*x*x))
                    D.rod(m,q+(-.1,0,-.23),q+(.1,0,.23),.035,'canvas_plain',sides=4)
    D.configure(m);m.material_overrides.update(MAPS);return m

def main():
    MODEL.mkdir(parents=True,exist_ok=True)
    L.RES=RES;L.MAPS=MAPS
    for i in range(3):
        model=build(i)
        K.write_obj(MODEL/f'lantern_lod{i}.obj',model,f'lantern_lod{i}')
        K.write_obj(MODEL/f'mirrored_lod{i}.obj',model.mirrored(),f'mirrored_lod{i}')
    doc=L.modeldoc()
    (MODEL/'sack_pile.vmdl').write_text(doc)
    (MODEL/'sack_pile_mirrored.vmdl').write_text(doc.replace('lantern_lod','mirrored_lod'))
    print('Accepted sack piles staged; retired review resources not recreated.')
if __name__=='__main__':main()
