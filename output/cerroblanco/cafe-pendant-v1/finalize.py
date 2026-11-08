from pathlib import Path
import shutil
R=Path('C:/sbox-projects/hc1/forked-shooter-main');o=R/'output/cerroblanco/cafe-pendant-v1'
for src,dst in [('bridge_window_170735_349.png','before.png'),('bridge_window_170740_187.png','after.png')]:shutil.copyfile(Path('C:/Users/leon2/AppData/Local/Temp')/src,o/dst)
