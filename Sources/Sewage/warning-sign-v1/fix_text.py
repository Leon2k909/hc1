"""Rebuild only the warning artwork using measured text bounds, retaining the source look."""
from pathlib import Path
import json,shutil,sys
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
OUT=ROOT/'output/sewage/warning-sign-v1/text-fit'
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'Tools'))
import sewage_map as R
from PIL import Image,ImageDraw,ImageFont
stage=OUT/'stage';stage.mkdir(exist_ok=True)
shutil.copyfile(ROOT/'Assets/materials/sewage/concrete_color.png',stage/'concrete_color.png')
R.MAT=stage
R.sign('warning',['WATCH','YOUR STEP'],size=(768,512),fit_text=True)
# Verify glyph extents before rasterisation: 10% minimum horizontal inset on both sides.
w,h=768,512;top=int(h*.08);avail=h-top-int(h*.08);fs=int(avail/2*.74)
draw=ImageDraw.Draw(Image.new('RGB',(w,h)))
while fs>1:
    font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',fs)
    boxes=[draw.textbbox((0,0),s,font=font) for s in ('WATCH','YOUR STEP')]
    if all(b[2]-b[0]<=int(w*.80) for b in boxes):break
    fs-=1
positions=[]
for i,(text,b) in enumerate(zip(('WATCH','YOUR STEP'),boxes)):
    width=b[2]-b[0];height=b[3]-b[1]
    left=(w-width)//2;rowcentre=top+(i+.5)*avail/2
    positions.append(dict(text=text,left=left,right=left+width,top=rowcentre-height/2,bottom=rowcentre+height/2))
assert min(p['left'] for p in positions)>=w*.10
assert max(p['right'] for p in positions)<=w*.90
assert positions[0]['bottom']<positions[1]['top']
(OUT/'layout.json').write_text(json.dumps(dict(font_size=fs,source_size=[w,h],final_size=list(Image.open(stage/'warning_color.png').size),lines=positions),indent=2))
# Reuse the exact model-review camera; capture one installed-model view per phase.
capture=(HERE/'capture-installed.cs.txt').read_text()
capture=capture.replace('var output=System.IO.Path.Combine(project,"output/sewage/warning-sign-v1");','var output=System.IO.Path.Combine(project,"output/sewage/warning-sign-v1/text-fit");\nvar phase=System.IO.File.ReadAllText(System.IO.Path.Combine(output,"phase.txt")).Trim();')
capture=capture.replace('foreach(var view in views)foreach(var variant in new[]{"before","after"})','foreach(var view in views.Where(v=>v.Name=="close"))foreach(var variant in new[]{"after"})')
capture=capture.replace('view.Name+"-"+variant+".png"','phase+".png"')
(HERE/'capture-text.cs.txt').write_text(capture)
(OUT/'phase.txt').write_text('before')
print((OUT/'layout.json').read_text())
