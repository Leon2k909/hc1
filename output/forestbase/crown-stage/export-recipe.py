# Offline source reproduction; run from HC1 without an S&box editor.
import subprocess,sys
from pathlib import Path
root=Path.cwd();stage=root/'output/forestbase/crown-stage'
blender=r'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'
subprocess.run([blender,'--background','--factory-startup','--threads','4','--python',str(root/'Tools/forestbase_crown_lods_blender.py'),'--','--output',str(stage/'models/maps/forestbase/fir')],check=True)
subprocess.run([sys.executable,str(root/'Tools/forestbase_crown_coverage.py'),'--output',str(stage/'models/maps/forestbase/fir'),'--legacy-input',str(root/'output/forestbase/crown-before/Assets/models/maps/forestbase/fir')],check=True)
subprocess.run([sys.executable,str(root/'Tools/forestbase_crown_audit.py')],check=True)
