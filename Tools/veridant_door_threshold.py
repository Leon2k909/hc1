"""Build the missing operations courtyard threshold without rebuilding the map."""
from pathlib import Path
import map_kit as K
import veridant_map as V

ROOT=Path(__file__).resolve().parent.parent
RESOURCE='models/maps/veridant/door-threshold-fix'

def main():
    m=K.Model()
    m.uv_source_name='veridant_buildings'
    V.floor(m,280.,360.,-336.,-320.,0.,'vr_floor')
    V.card(m,'vr_stone',[V.v(280,-320,0),V.v(360,-320,0),V.v(360,-320,14.5),V.v(280,-320,14.5)],V.v(0,-1,0))
    V.configure(m)
    dest=ROOT/'output/veridant/door-threshold-fix/stage'/RESOURCE
    K.write_model(dest,RESOURCE,'courtyard_threshold',m)
    print(f'{m.triangle_count()} triangles, floor flush at z=0 plus missing deck riser; existing collision retained')

if __name__=='__main__': main()
