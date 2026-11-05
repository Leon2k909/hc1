"""Encode the native test frames as a small looping animation for review."""
from pathlib import Path
from PIL import Image
root=Path(__file__).resolve().parents[3]
folder=root/'output/zombie-hit-reactions-20261104'
paths=[folder/'neutral.png',*sorted(folder.glob('motion-*.png')),folder/'recovered.png']
images=[Image.open(p).convert('RGB').resize((960,667),Image.Resampling.LANCZOS) for p in paths]
palette=images[0].quantize(colors=256)
frames=[image.quantize(palette=palette,dither=Image.Dither.NONE) for image in images]
frames[0].save(folder/'hit-reaction.gif',save_all=True,append_images=frames[1:],duration=[700]+[33]*(len(frames)-2)+[600],loop=0,optimize=False)
print(folder/'hit-reaction.gif')
