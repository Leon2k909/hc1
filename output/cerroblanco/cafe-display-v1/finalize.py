from pathlib import Path
import shutil
R=Path('C:/sbox-projects/hc1/forked-shooter-main');o=R/'output/cerroblanco/cafe-display-v1'
for src,dst in [('bridge_window_160856_190.png','before.png'),('bridge_window_160900_703.png','after.png')]:shutil.copyfile(Path('C:/Users/leon2/AppData/Local/Temp')/src,o/dst)
