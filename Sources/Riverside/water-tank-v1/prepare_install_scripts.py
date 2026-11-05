"""Prepare the approved vessel-only installation; no B resources are used."""
from pathlib import Path
HERE=Path(__file__).absolute().parent;OLD=HERE.parent/'trailer-hitch-v1'
def rename(t):
    for a,b in [('trailer-hitch-v1','water-tank-v1'),('trailer_hitch_v1','water_tank_v1'),('low_without_hitch','backdrop_without_tank'),('legacy_hitch','legacy_tank'),('hitch.vmdl','tank.vmdl'),('riverside_low','riverside_backdrop'),('low_vmdl_before','backdrop_vmdl_before'),('low.vmdl','backdrop.vmdl'),('install-stage/low.obj','install-stage/backdrop.obj'),('Trailer Hitches','Water Tower Tanks'),('T2 Trailer Hitch','Riverside Water Tank'),('8422,5470,1526','11788,7288,3316'),('1050,1030,0','3600,-1688,1196'),('==48','==224'),('=48','=224'),('OnlyOriginalHitchRemoved','OnlyOriginalTankRemoved'),('OriginalLowlandModelDocPreserved','OriginalBackdropModelDocPreserved'),('Hitches=1','Tanks=1')]:t=t.replace(a,b)
    return t
for name in ('prepare_install.py','install.py','finish_install.py'):(HERE/name).write_text(rename((OLD/name).read_text()))
t=rename((OLD/'check_installed.py').read_text())
t=t.replace("code=code.replace('\"Roof TV Aerials\"','\"Roof TV Aerials\", \"Water Tower Tanks\"')", "code=code.replace('\"Trailer Hitches\"','\"Trailer Hitches\", \"Water Tower Tanks\"')")
(HERE/'check_installed.py').write_text(t)
print('A installation scripts prepared')
