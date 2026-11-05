from pathlib import Path
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main')
HERE=Path(__file__).parent
source=(ROOT/'Sources/Riverside/ice-cabinet-v1/import.cs.txt').read_text()
source=source.replace('C:/sbox-projects/hc1/ice-cabinet-review','C:/sbox-projects/hc1/register-review').replace('ice-cabinet-v1','register-v1')
(HERE/'import.cs.txt').write_text(source)
source=(ROOT/'Sources/Riverside/ice-cabinet-v1/isolated-review.cs.txt').read_text()
source=source.replace('C:/sbox-projects/hc1/ice-cabinet-review','C:/sbox-projects/hc1/register-review').replace('ice-cabinet-v1','register-v1').replace('legacy_ice.vmdl','legacy_register.vmdl').replace('ice_cabinet.vmdl','register.vmdl')
source=source.replace('new Vector3(-96,-73,64)','new Vector3(-25,-27,22)').replace('new Vector3(0,0,30)','new Vector3(0,0,5)').replace('FieldOfView=42','FieldOfView=38')
source=source.replace('new Vector3(-70,-65,95),260','new Vector3(-30,-40,55),150').replace('new Vector3(30,50,65),210','new Vector3(20,30,35),130')
(HERE/'isolated-review.cs.txt').write_text(source)
