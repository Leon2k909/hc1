from pathlib import Path
import shutil
OUT=Path('C:/sbox-projects/hc1/forked-shooter-main/output/cerroblanco/cafe-grinder-v1')
for src,dst in [('bridge_window_155727_498.png','before.png'),('bridge_window_155822_358.png','after.png')]:
    shutil.copyfile(Path('C:/Users/leon2/AppData/Local/Temp')/src,OUT/dst)
