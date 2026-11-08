from pathlib import Path
import shutil
R=Path('C:/sbox-projects/hc1/forked-shooter-main');o=R/'output/cerroblanco/courtyard-cctv-v1'
for src,dst in [('bridge_window_171143_556.png','before.png'),('bridge_window_171147_108.png','after.png')]:shutil.copyfile(Path('C:/Users/leon2/AppData/Local/Temp')/src,o/dst)
