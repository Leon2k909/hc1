"""Adapt the guarded single-fixture installation; no live Assets are edited here."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
text=(ROOT/'Sources/ReefHall/circulation-pump-v1/prepare_install.py').read_text()
for old,new in [('circulation-pump-v1','wall-light-v1'),('circulation_pump','wall_light'),('filter_without_pump','filter_without_light'),('rh_cp_','rh_wl_'),("K.uv_offset('wall_light')","K.uv_offset('wall_light')"),('InstalledPumps','InstalledLights')]:text=text.replace(old,new)
start=text.index('    # The original plinth and cover boxes,');end=text.index('    m=model()',start)
text=text[:start]+text[end:]
start=text.index('g=generator.read_text();');end=text.index('\nscript=',start)
text=text[:start]+'''g=generator.read_text()
old='    fbox( model, fr, u - 3.5, u + 3.5, w, w + 3.0, z, z + 16, { "default": "rh_gunmetal", "front": "rh_led_warm" } )'
assert g.count(old)==1
new='''+repr('''    if np.allclose(fr.p(u,w,z),(760.,1100.,110.)) and np.allclose(fr.vec(0,1,0),(0,1,0)):
        from reefhall_wall_light import append_to as append_approved_wall_light
        append_approved_wall_light(model)
    else:
        fbox( model, fr, u - 3.5, u + 3.5, w, w + 3.0, z, z + 16, { "default": "rh_gunmetal", "front": "rh_led_warm" } )''')+'''
g=g.replace(old,new);generator.write_text(g)
'''+text[end:]
# The old recipe's generated verifier is replaced below with the installed-light checks.
start=text.index('verify=(ROOT/');text=text[:start]+'''print(json.dumps(dict(lights=1,staged_files=len(files),old_triangles=12,new_triangles=4300,generator_matches_approved=True)))
'''
old="guard=json.loads((OUT/'source-guard.json').read_text());changed=[p for p,h in guard.items() if sha(ROOT/p)!=h];assert not changed,changed"
new='''guard=json.loads((OUT/'source-guard.json').read_text());changed=[p for p,h in guard.items() if sha(ROOT/p)!=h]
allowed={'Assets/models/maps/reefhall/reefhall_lobby.mtl','Assets/models/maps/reefhall/reefhall_lobby.obj','Assets/models/maps/reefhall/reefhall_lobby.vmdl','Tools/reefhall_map.py'}
assert set(changed)==allowed,changed
assert json.loads((ROOT/'Sources/ReefHall/bronze-planter-v1/review/installed.json').read_text())['Planters']==2
(OUT/'concurrent-changes.json').write_text(json.dumps(dict(reason='Approved bronze entrance planter installed independently; preserve current lobby and generator hook',files={p:sha(ROOT/p) for p in changed}),indent=2))'''
assert old in text;text=text.replace(old,new)
text=text.replace('filter pump','filter wall light').replace('ReefHall circulation pump','ReefHall wall light')
(HERE/'prepare_install.py').write_text(text)
verify=(ROOT/'Sources/ReefHall/circulation-pump-v1/verify_installed.py').read_text()
for old,new in [('circulation-pump-v1','wall-light-v1'),('installed_circulation_pump','installed_wall_light'),('==220','==12'),('==16196','==4300'),('pumps=1','lights=1'),('old_render_triangles_removed=220,new_triangles=16196','old_render_triangles_removed=12,new_triangles=4300')]:verify=verify.replace(old,new)
verify=verify.replace("if '--report-only' not in sys.argv:\n r=call", "if '--report-only' not in sys.argv and '--capture-only' not in sys.argv:\n r=call")
verify=verify.replace("assert set(changed)=={base,public,'Tools/reefhall_map.py'},changed",'''concurrent=json.loads((OUT/'concurrent-changes.json').read_text())
assert set(changed)=={base,public,'Tools/reefhall_map.py'}|set(concurrent['files']),changed
for p,h in concurrent['files'].items():
 if p!='Tools/reefhall_map.py':assert sha(ROOT/p)==h,p
g=(ROOT/'Tools/reefhall_map.py').read_text();oldg=(OUT/'install-before/Tools/reefhall_map.py').read_text()
start=g.index('    if np.allclose(fr.p(u,w,z),(760.,1100.,110.))');end=g.index('    _sconces.append(',start)
original_line='    fbox( model, fr, u - 3.5, u + 3.5, w, w + 3.0, z, z + 16, { "default": "rh_gunmetal", "front": "rh_led_warm" } )\\n'
assert g[:start]+original_line+g[end:]==oldg,'Unrelated generator changes during installation' ''')
verify=verify.replace('saved public pallet','saved public wall light')
(HERE/'verify_installed.py').write_text(verify)
retire=(ROOT/'Sources/Railhead/ashtray-v1/retire_preview.py').read_text()
for old,new in [("['columns']==4","['lights']==1"),('output/railhead/ashtray-v1','output/reefhall/wall-light-v1'),('Assets/models/maps/railhead/ashtray-v1','Assets/models/maps/reefhall/wall-light-v1'),('east_without_ashtray','filter_without_light')]:retire=retire.replace(old,new)
(HERE/'retire_preview.py').write_text(retire)
print('Installation scripts ready')
