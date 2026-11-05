"""Adapt the verified aerial install workflow to this approved hitch."""
from pathlib import Path
HERE=Path(__file__).absolute().parent;OLD=HERE.parent/'tv-aerial-v1'
def rename(t):
    for a,b in [('tv-aerial-v1','trailer-hitch-v1'),('tv_aerial_v1','trailer_hitch_v1'),('legacy_aerial','legacy_hitch'),('low_without_aerial','low_without_hitch'),('aerial.vmdl','hitch.vmdl'),('aerials','hitches'),('aerial','hitch'),('Aerials','Hitches'),('Aerial','Hitch'),('Roof TV Hitches','Trailer Hitches'),('T2 Rooftop TV Hitch','T2 Trailer Hitch'),('3912,2468,912','8422,5470,1526'),('==52','==48'),('=52','=48'),('= 52','= 48'),('=26','=24'),('1033.5,794.7722080465406,123','1050,1030,0')]:t=t.replace(a,b)
    return t
for name in ('prepare_install.py','install.py','finish_install.py'):
    t=rename((OLD/name).read_text())
    if name=='install.py':
        t=t.replace("    assert not status['IsPlaying'],'Scene installation requires edit mode.'", "    if status['IsPlaying']: e.call('play_stop')")
        t=t.replace("            e.call('switch_scene',dict(scene=status['ActiveScenePath']))", "            e.call('switch_scene',dict(scene=status['ActiveScenePath']))\n            if status['IsPlaying']: e.call('play_start')")
    (HERE/name).write_text(t)
t=rename((OLD/'check_installed.py').read_text())
# The hitch capture's visual roots include its own group, while retaining the approved aerial.
t=t.replace("code=code.replace('\"Street Lights\"','\"Street Lights\", \"Trailer Hitches\"')", "code=code.replace('\"Roof TV Aerials\"','\"Roof TV Aerials\", \"Trailer Hitches\"')")
(HERE/'check_installed.py').write_text(t)
print('Hitch installation scripts prepared')
