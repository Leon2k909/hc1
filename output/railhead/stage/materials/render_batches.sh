#!/bin/bash
# usage: render_batches.sh <stage> <outdir> ; renders the materials agent's views in batches of 4, one after another
ROOT="/d/Documents/s&box projects/hc1/forked-shooter-main"
STAGE="$1"; OUT="$2"; shift 2
cd "$ROOT"
V_PAVE="mat_paving_close,632,300,64,632,480,8,70"
V_SAND="mat_sandstone_close,1040,200,64,1200,280,130,60"
V_PLAS="mat_plaster_close,-300,1450,64,-600,1560,220,70"
V_TERR="mat_terrazzo_close,0,1480,64,80,1640,0,70"
V_BRICK="mat_brick_close,1400,-1950,64,1520,-1850,100,60"
V_STEEL="mat_steel_close,70,380,64,0,470,160,60"
V_GLASS="mat_glass_roof,632,0,64,632,260,620,70"
V_BALL="mat_ballast_close,500,-200,64,416,-330,-30,65"
V_ASPH="mat_asphalt_close,1480,300,64,1620,520,-6,70"
V_CAN="mat_canopy_steel,632,-900,64,700,-1000,120,60"
R(){ python output/railhead/stage/render.py --max-wait 3000 --stage "$STAGE" --out "$OUT" --size 960x540 --samples 32 "$@"; }
for B in "$@"; do
 case $B in
  1) R --views "" --view $V_PAVE --view $V_SAND --view $V_PLAS --view $V_TERR ;;
  2) R --views "" --view $V_BRICK --view $V_STEEL --view $V_GLASS --view $V_BALL ;;
  3) R --views reference,platform_b --view $V_ASPH --view $V_CAN ;;
  4) R --views booking_hall,hall_floor,goods_yard,throat ;;
  5) R --views concourse,footbridge,cab_road,signal_box ;;
  6) R --views reference_wide,platform_c_north ;;
 esac
done
