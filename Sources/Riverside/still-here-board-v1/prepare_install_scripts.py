from pathlib import Path
HERE=Path(__file__).absolute().parent;OLD=HERE.parent/'water-tank-v1'
def rename(t):
 for a,b in [('water-tank-v1','still-here-board-v1'),('water_tank_v1','still_here_board_v1'),('backdrop_without_tank','dressing_without_board'),('legacy_tank','legacy_board'),('tank.vmdl','board.vmdl'),('riverside_backdrop','riverside_dressing'),('backdrop_vmdl_before','dressing_vmdl_before'),('backdrop.vmdl','dressing.vmdl'),('install-stage/backdrop.obj','install-stage/dressing.obj'),('Water Tower Tanks','Park Graffiti Boards'),('Riverside Water Tank','STILL HERE Board'),('11788,7288,3316','896,752,144'),('3600,-1688,1196','411.535923789485,390.99995599854793,261.25'),('==224','==14'),('=224','=14'),('OnlyOriginalTankRemoved','OnlyOriginalBoardRemoved'),('OriginalBackdropModelDocPreserved','OriginalDressingModelDocPreserved'),('Tanks=1','Boards=1')]:t=t.replace(a,b)
 return t
for name in ('prepare_install.py','install.py','finish_install.py'):
 t=rename((OLD/name).read_text())
 if name=='install.py':t=t.replace('position:"411.535923789485,390.99995599854793,261.25"','position:"411.535923789485,390.99995599854793,261.25",angles:"0,30.000727780827372,0"')
 (HERE/name).write_text(t)
t=rename((OLD/'check_installed.py').read_text());(HERE/'check_installed.py').write_text(t)
