from pathlib import Path
import shutil
OUT=Path('C:/sbox-projects/hc1/forked-shooter-main/output/cerroblanco/courtyard-bin-v1')
for src,dst in [('bridge_window_151920_650.png','before.png'),('bridge_window_151918_636.png','after.png'),('bridge_window_151845_373.png','before-context.png'),('bridge_window_151847_460.png','after-context.png')]:
    shutil.copyfile(Path('C:/Users/leon2/AppData/Local/Temp')/src,OUT/dst)
