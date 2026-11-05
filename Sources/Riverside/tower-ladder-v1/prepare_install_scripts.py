from pathlib import Path
HERE=Path(__file__).absolute().parent;OLD=HERE.parent/'water-tank-v1'
def rename(t):
    for a,b in [('water-tank-v1','tower-ladder-v1'),('water_tank_v1','tower_ladder_v1'),('backdrop_without_tank','dressing_without_ladder'),('legacy_tank','legacy_ladder'),('tank.vmdl','ladder.vmdl'),('riverside_backdrop','riverside_dressing'),('backdrop_vmdl_before','dressing_vmdl_before'),('backdrop.vmdl','dressing.vmdl'),('install-stage/backdrop.obj','install-stage/dressing.obj'),('Water Tower Tanks','Guard Tower Ladders'),('Riverside Water Tank','Guard Tower Ladder'),('11788,7288,3316','15136,9876,4660'),('3600,-1688,1196','1684.2887130994613,555.2866139298384,0'),('==224','==450'),('=224','=450'),('OnlyOriginalTankRemoved','OnlyOriginalLadderRemoved'),('OriginalBackdropModelDocPreserved','OriginalDressingModelDocPreserved'),('Tanks=1','Ladders=1')]:t=t.replace(a,b)
    return t
for name in ('prepare_install.py','install.py'):
    t=rename((OLD/name).read_text())
    if name=='install.py':t=t.replace('position:"1684.2887130994613,555.2866139298384,0"','position:"1684.2887130994613,555.2866139298384,0",angles:"0,-163.3007557660064,0"')
    (HERE/name).write_text(t)
t=rename((OLD/'check_installed.py').read_text()).replace("'\"Trailer Hitches\", \"Guard Tower Ladders\"'","'\"Trailer Hitches\", \"Water Tower Tanks\", \"Guard Tower Ladders\"'")
(HERE/'check_installed.py').write_text(t)
