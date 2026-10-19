#!/bin/bash
# usage: round.sh <tag> ; builds the stage, cleans others' materials, renders the round's views
cd "/d/Documents/s&box projects/hc1/forked-shooter-main"
S="$PWD/output/railhead/stage/r2_structure"
T=$1
python Tools/railhead_structure_paints.py "$S" > /dev/null
python Tools/railhead_map.py --stage "$S" > "$S/logs/build_$T.log" 2>&1 || exit 1
rm -rf "$S/materials/railhead/dress" "$S/materials/railhead/finish"
r() { for i in 1 2 3 4; do python output/railhead/stage/render.py --stage "$S" --out "$S/renders/$T" "$@" --size 960x540 --samples 32 >> "$S/logs/render_$T.log" 2>&1 && return; done; }
r --views platform_b --view stair_close,140,120,64,60,-120,150,55 --view goods_door2,1300,-1640,110,1520,-1900,120,60 --view roof_soffit,300,100,64,560,300,540,75
r --views reference --view arcade_in,900,-300,64,1160,-150,200,60 --view canopy_col,700,-1350,64,632,-1600,90,60 --view rib_node,400,-30,64,600,200,560,45
echo done
