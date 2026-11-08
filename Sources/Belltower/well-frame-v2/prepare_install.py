from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
s=(ROOT/'Sources/Belltower/market-cross-v2/install_prepare.py').read_text().replace('market-cross-v2','well-frame-v2').replace('market_cross','well_frame').replace('Market cross model','Garden well frame').replace('Market cross','Garden well frame')
a=s.index('old=K.Model()');b=s.index('docs=',a)
s=s[:a]+'''old=K.Model();e,n=B.GARDEN_WELL;z=B.GARDEN_Z
for se in (-1,1):old.box((e+se*38-4,n-4,z+34),(e+se*38+4,n+4,z+116),'planks_dark')
old.beam((e-44,n,z+106),(e+44,n,z+106),(6,6),'planks_dark')
B.axle(old,(e,n,z+96),(1,0,0),6,50,{'side':'planks','end':'planks_dark'});wanted=geometry(old)
'''+s[b:]
s=s.replace("r.endswith('_ashlar.obj')","re.search(r'_(planks|planks_dark)\\.obj$',r)")
s=s.replace('==40','==72').replace("'old_triangles_removed':40","'old_triangles_removed':72").replace("replace('3038','40')","replace('3038','72')").replace('K.to_world((0,1275,0))','K.to_world((0,-1225,-48))')
(HERE/'install_prepare.py').write_text(s)
