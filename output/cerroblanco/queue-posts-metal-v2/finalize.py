from pathlib import Path
import shutil
R=Path('C:/sbox-projects/hc1/forked-shooter-main');o=R/'output/cerroblanco/queue-posts-metal-v2'
for src,dst in [('bridge_window_163143_756.png','before.png'),('bridge_window_163147_438.png','after.png')]:shutil.copyfile(Path('C:/Users/leon2/AppData/Local/Temp')/src,o/dst)
