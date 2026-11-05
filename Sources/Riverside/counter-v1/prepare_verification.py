from pathlib import Path
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');HERE=Path(__file__).parent
source=(ROOT/'Sources/Riverside/register-v1/verify.py').read_text()
source=source.replace('C:/sbox-projects/hc1/register-review','C:/sbox-projects/hc1/counter-review').replace('register-v1','counter-v1').replace('register_lod','counter_lod').replace('store_without_register','store_without_counter')
source=source.replace("'in-game-before.png'","'in-game-front-before.png'").replace("'in-game-after.png'","'in-game-front-after.png'")
source=source.replace("assert np.mean(abs(np.asarray(before,dtype=float)-np.asarray(after,dtype=float)))>2", """assert np.mean(abs(np.asarray(before,dtype=float)-np.asarray(after,dtype=float)))>2
# Gameplay auto-exposure changes with the counter albedo. Check wall alignment
# with brightness-normalized data for QA only; displayed captures stay unedited.
ba=np.asarray(before,dtype=float)[:130,:300];bb=np.asarray(after,dtype=float)[:130,:300]
aa=ba-ba.mean((0,1));bc=bb-bb.mean((0,1))
correlation=float((aa*bc).sum()/np.sqrt((aa*aa).sum()*(bc*bc).sum()))
assert correlation>.99,correlation""")
source=source.replace("geometry=checks)","geometry=checks,matching_camera_alignment_correlation=correlation)")
source=source.replace("m=json.loads((OUT/'manifest.json').read_text())","m=json.loads((OUT/'manifest.json').read_text())\nassert json.loads((OUT/'materials-verified.json').read_text())['AllMaterialsLoaded']")
source=source.replace("assert all(sha(ROOT/p)==h for p,h in m['files'].items())","assert all(sha(ROOT/p)==h for p,h in m['files'].items())\nassert all(sha(ROOT/p)==h for p,h in m['external_files'].items())")
source=source.replace("v=np.asarray(vertices);n=np.asarray(normals)","v=np.asarray(vertices);n=np.asarray(normals)\n    # OBJ source is Y-up: X is width, Y is height, Z is depth.\n    assert np.max(abs(v[:,0]))<=55.001 and v[:,1].min()>=0 and v[:,1].max()<=40.001 and np.max(abs(v[:,2]))<15.03")
(HERE/'verify.py').write_text(source)
