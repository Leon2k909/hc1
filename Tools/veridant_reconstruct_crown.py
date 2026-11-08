"""Run the installed local reconstruction pipeline without overwriting the lion source."""
from pathlib import Path
import sys

root = Path(sys.argv[1])
script = root / 'reconstruct.py'
sys.argv = [str(script), sys.argv[2]]
source = script.read_text(encoding='utf-8-sig')
source = source.replace('final_size = 320', 'final_size = 384')
source = source.replace('root / "lion.glb"', 'root / "crown-v2.glb"')
exec(compile(source, str(script), 'exec'), {'__file__': str(script), '__name__': '__main__'})
