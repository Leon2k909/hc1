from pathlib import Path
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main')
source=ROOT/'Sources/Sewage/tower-vents-v1/build.py'
scope={'__file__':str(source),'__name__':'comparison_build'}
exec(source.read_text().split('all_vents=K.Model()')[0],scope)
K,R=scope['K'],scope['R']
stage=scope['STAGE']
old=R.model()
old.cylinder((0,0),26,0,53,'steel',sides=16)
old.cylinder((0,0),29,50,56,'rust',sides=16)
K.write_model(stage,'models/maps/sewage/tower-vents-v1','compare_old',old)
K.write_model(stage,'models/maps/sewage/tower-vents-v1','compare_new',scope['vent'])
print('Staged two local comparison models')
