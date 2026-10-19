#!/bin/bash
# usage: renders.sh <round>   (renders after views; also before3 if missing)
cd "/d/Documents/s&box projects/hc1/forked-shooter-main"
S="D:/Documents/s&box projects/hc1/forked-shooter-main/output/railhead/stage/r2_dressing"
R="$1"; shift
mkdir -p "$S/renders/$R"
run() { # out stage args...
  local out="$1"; local st="$2"; shift 2
  for t in 1 2 3; do
    python output/railhead/stage/render.py --stage "$st" --out "$out" "$@" --size 960x540 --samples 32 >> "$S/logs/render_$R.log" 2>&1
    c=$?; [ $c -ne 3 ] && return $c
  done
}
B1="--views road_wear_close --view road_wear_close,1660,-520,60,1700,-120,-6,70 --view under_bridge,632,-60,66,632,-330,170,70 --view bridge_signs,0,-280,278,600,-280,260,70 --view rank_pavement,1420,600,66,1330,1180,40,70"
run "$S/renders/$R" "$S" --view road_wear_close,1660,-520,60,1700,-120,-6,70 --view under_bridge,632,-60,66,632,-330,170,70 --view bridge_signs,0,-280,278,600,-280,260,70 --view rank_pavement,1420,600,66,1330,1180,40,70
run "$S/renders/$R" "$S" --views platform_b,footbridge,hall_floor,goods_yard
if [ ! -f "$S/renders/before/hall_clock.png" ]; then
  run "$S/renders/before" "$S/empty" --views cab_road --view smoking_zone,520,-1080,66,620,-1200,0,70 --view hall_clock,0,1760,66,0,1500,300,70 --view yard_close,1820,-1300,66,1900,-1600,0,70
fi
run "$S/renders/$R" "$S" --views cab_road --view smoking_zone,520,-1080,66,620,-1200,0,70 --view hall_clock,0,1760,66,0,1500,300,70 --view yard_close,1820,-1300,66,1900,-1600,0,70
echo ALLDONE >> "$S/logs/render_$R.log"
