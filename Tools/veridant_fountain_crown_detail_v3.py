"""Retain finer facial and mane geometry from the reference reconstruction."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
source = (root / 'Tools/veridant_fountain_reference_crown_v2.py').read_text()
source = source.replace("DEST = ROOT / 'Assets/models/props/shared/veridant_fountain_reference_top_v2'", "DEST = ROOT / 'Assets/models/props/shared/veridant_fountain_reference_top_v3'")
source = source.replace('pitch=.0085', 'pitch=.005')
source = source.replace('iterations=3', 'iterations=1')
source = source.replace('solid.astype(float), .8', 'solid.astype(float), .45')
source = source.replace('target_count=220000', 'target_count=380000')
source = source.replace("'veridant_fountain_reference_top_v2/crown.obj'", "'veridant_fountain_reference_top_v3/crown.obj'")
source = source.replace("shutil.copy2(path, SOURCE / 'crown.glb')", "# Preserve the original reconstruction")
exec(compile(source, __file__, 'exec'), {'__file__': __file__, '__name__': '__main__'})
