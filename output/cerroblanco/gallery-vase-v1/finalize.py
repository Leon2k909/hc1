from pathlib import Path
import shutil,json
OUT=Path('C:/sbox-projects/hc1/forked-shooter-main/output/cerroblanco/gallery-vase-v1')
for src,dst in [('bridge_window_154519_575.png','before.png'),('bridge_window_154523_429.png','after.png')]:
    shutil.copyfile(Path('C:/Users/leon2/AppData/Local/Temp')/src,OUT/dst)
