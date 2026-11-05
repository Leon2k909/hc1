from pathlib import Path
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');HERE=Path(__file__).parent
for name in ('native.py','import.cs.txt'):
    base='shop-sign-v1' if name=='native.py' else 'shelving-v1'
    s=(ROOT/f'Sources/Riverside/{base}/{name}').read_text(encoding='utf-8').replace(base,'neon-sign-v1').replace('shelving-review','neon-sign-review')
    (HERE/name).write_text(s,encoding='utf-8')
s=(ROOT/'Sources/Riverside/water-tower-v1/check_geometry.py').read_text(encoding='utf-8').replace('water-tower-v1','neon-sign-v1').replace('tower_lod','neon_lod').replace('np.max(abs(v[:,0]))<270','np.max(abs(v[:,0]))<=57.001').replace('v[:,1].max()==1476','v[:,1].max()<476').replace('np.max(abs(v[:,2]))<270','np.max(abs(v[:,2]))<9')
(HERE/'check_geometry.py').write_text(s,encoding='utf-8')
