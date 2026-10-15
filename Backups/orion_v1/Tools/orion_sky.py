"""Original muted late-afternoon HDR sky, generated into Orion's staging directory."""
from pathlib import Path
import numpy as np
import belltower_sky as S

def main():
    S.OUT_DIR=Path(__file__).resolve().parents[1]/"output/orion/stage/materials/orion/sky"
    S.RESOURCE_DIR="materials/orion/sky";S.NAME="orion_sky"
    # The sun sits to the west of the main view, just beyond the left-hand building.
    S.SUN_PITCH=18.;S.SUN_YAW=-150.
    S.DESIGN_EXPOSURE=1.2
    S.SKY_KEYS=((0.,(211,197,178)),(6.,(189,184,178)),(15.,(157,170,184)),
                (30.,(119,145,173)),(55.,(94,121,153)),(90.,(83,109,143)))
    S.LIGHT=np.array((1.7,1.29,.84));S.CLOUD_SUN=S.LIGHT*1.1
    S.AMB_HIGH=np.array((.19,.28,.44));S.AMB_LOW=np.array((.26,.24,.22))
    S.HEAPS=.15;S.PUFF_GROUPS=.11;S.SUN_HALO=.9
    S.HEAP_SIZE=(330.,.5,130.,1000.);S.HEAP_HEIGHT=(.35,.8)
    S.NEAR_SIZE=(350.,.3,210.,530.);S.NEAR_RING=(5000.,10000.)
    S.main()

if __name__=="__main__":main()
