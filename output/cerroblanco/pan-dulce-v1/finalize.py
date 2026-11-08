from pathlib import Path
import shutil
R=Path('C:/sbox-projects/hc1/forked-shooter-main');o=R/'output/cerroblanco/pan-dulce-v1'
for src,dst in [('bridge_window_161453_240.png','before.png'),('bridge_window_161457_218.png','after.png')]:shutil.copyfile(Path('C:/Users/leon2/AppData/Local/Temp')/src,o/dst)
