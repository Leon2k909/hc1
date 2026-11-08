from pathlib import Path
import sys
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,veridant_map as V,veridant_operations_counter as B
m=K.Model();m.uv_source_name='veridant_buildings';B.build_into(m);V.configure(m)
res='models/props/shared/operations_counter_v1';K.write_model(ROOT/'output/veridant/operations-counter-v1/stage'/res,res,'counter',m)
