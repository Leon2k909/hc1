from pathlib import Path
import shutil
R=Path('C:/sbox-projects/hc1/forked-shooter-main');o=R/'output/cerroblanco/queue-posts-v1'
for src,dst in [('bridge_window_162108_375.png','before.png'),('bridge_window_162243_057.png','after.png')]:shutil.copyfile(Path('C:/Users/leon2/AppData/Local/Temp')/src,o/dst)
