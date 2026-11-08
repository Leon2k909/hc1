from pathlib import Path
import shutil
OUT=Path('C:/sbox-projects/hc1/forked-shooter-main/output/cerroblanco/courtyard-bench-piers-v1')
for src,dst in [('bridge_window_143428_562.png','before.png'),('bridge_window_143430_421.png','after.png')]:
    shutil.copyfile(Path('C:/Users/leon2/AppData/Local/Temp')/src,OUT/dst)
