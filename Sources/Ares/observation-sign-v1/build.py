"""Build a private, native-engine sign candidate; never overwrite installed map content."""
from pathlib import Path
import sys,json,hashlib,math,re
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import ares_map as A
OUT=ROOT/'output/ares/observation-sign-v1'
STAGE=OUT/'stage'
RES='models/maps/ares/observation-sign-v1'
MAT='materials/ares/observation-sign-v1'
MODEL=STAGE/'Assets'/RES
MATERIAL=STAGE/'Assets'/MAT
MODEL.mkdir(parents=True,exist_ok=True);MATERIAL.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
guardpaths=list((ROOT/'Assets/models/maps/ares').rglob('*'))+list((ROOT/'Assets/materials/ares').rglob('*'))+[ROOT/'Assets/scenes/maps/Ares/ares.scene',ROOT/'Tools/ares_map.py',ROOT/'Tools/ares_materials.py']
guard={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in guardpaths if p.is_file() and p.suffix not in ('.meta',) and not p.name.endswith('_c') and 'observation-sign-v1' not in p.parts}
if not (OUT/'source-guard.json').exists():(OUT/'source-guard.json').write_text(json.dumps(guard,indent=2))

# A purpose-drawn, power-of-two wayfinding face with the project's Dinish font.
im=Image.new('RGB',(2048,512),(21,28,31));d=ImageDraw.Draw(im)
mask=Image.new('L',im.size,0);md=ImageDraw.Draw(mask)
font=ROOT/'Assets/fonts/Dinish-Bold.ttf'
def text(x,y,words,size,fill,glow=0):
    f=ImageFont.truetype(str(font),size)
    d.text((x,y),words,font=f,fill=fill,anchor='lt')
    if glow:md.text((x,y),words,font=f,fill=glow,anchor='lt')
d.rectangle((52,50,64,458),fill=(162,65,40))
text(102,54,'ARES  /  FACILITY',39,(159,169,166),40)
main_size=200
while ImageFont.truetype(str(font),main_size).getlength('OBSERVATION DECK')>1830:main_size-=1
text(102,153,'OBSERVATION DECK',main_size,(222,230,220),220)
d.line((103,354,1938,354),fill=(64,78,79),width=3)
text(103,396,'NORTH GALLERY',35,(138,154,151),30)
text(1585,396,'LEVEL 01',35,(138,154,151),30)
# Restrained sky/horizon pictogram, sized as a secondary identifier.
d.ellipse((1815,30,1911,126),outline=(134,160,157),width=4)
d.line((1828,91,1898,91),fill=(134,160,157),width=4)
d.arc((1842,62,1884,104),180,360,fill=(211,191,141),width=4)
im.save(MATERIAL/'face_color.png');mask.save(MATERIAL/'face_illum.png')
(MATERIAL/'face.vmat').write_text('''"Layer0"
{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 g_flMetalness "0.0"
 g_flRoughnessScaleFactor "1"
 TextureColor "'''+MAT+'''/face_color.png"
 TextureNormal "materials/default/default_normal.tga"
 TextureRoughness "[0.62 0.62 0.62 0]"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_vColorTint "[1 1 1 1]"
 F_SELF_ILLUM "1"
 TextureSelfIllumMask "'''+MAT+'''/face_illum.png"
 g_flSelfIllumBrightness "1.6"
 g_flSelfIllumAlbedoFactor "1"
 g_vSelfIllumTint "[1 0.98 0.92 0]"
}
''')
m=K.Model()
def P(x,depth,z):return np.array((x,600-depth,420+z),float)
def outline(w,h,c):
    return [(-w/2+c,-h/2),(w/2-c,-h/2),(w/2,-h/2+c),(w/2,h/2-c),(w/2-c,h/2),(-w/2+c,h/2),(-w/2,h/2-c),(-w/2,-h/2+c)]
def ring(w,h,c,depth):return [P(x,depth,z) for x,z in outline(w,h,c)]
def join(a,b,paint):
    for j in range(8):m.polygon(paint,[a[j],a[(j+1)%8],b[(j+1)%8],b[j]])
def shell():
    # Closed rear, chamfered powder-coated casting, inset rubber seal and lens lip.
    a,b,c,e=ring(190,46,3,-3.2),ring(194,50,4,-1.2),ring(194,50,4,1.8),ring(190,46,3,3.1)
    m.polygon('dark',a[::-1]);join(a,b,'alloy');join(b,c,'panel');join(c,e,'panel')
    f=ring(181.5,40.5,1.6,3.1);join(e,f,'panel')
    g=ring(180.5,39.5,1.3,2.7);join(f,g,'gasket')
    h=ring(180,39,1.1,2.65);join(g,h,'dark')
    # Recessed face does not share a plane with the frame.
    m.polygon('face',[P(-90,2.64,-19.5),P(90,2.64,-19.5),P(90,2.64,19.5),P(-90,2.64,19.5)],normal=(0,-1,0),uv=[(0,0),(1,0),(1,1),(0,1)])
shell()
def box(x,d,z,w,depth,h,paint):
    m.oriented_box(P(x,d,z),((1,0,0),(0,1,0),(0,0,1)),(w,depth,h),paint)
def rod(a,b,r,paint,sides=12):A.rod(m,a,b,r,paint,sides=sides)
# Captive fasteners sit on the metal margin, with recessed dark slots.
for x in (-93,93):
    for z in (-17,17):
        rod(P(x,3.08,z),P(x,3.26,z),.85,'alloy',12)
        box(x,3.28,z,.75,.03,.14,'dark')
# Cast end caps and rear service panel, deliberately kept within the old outer envelope.
for x in (-96,96):
    for z in (-11,-5,1,7,13):box(x,0,z,.22,2.5,.65,'dark')
box(0,-3.3,0,156,.16,30,'dark')
for x in (-74,74):
    for z in (-11,11):rod(P(x,-3.4,z),P(x,-3.6,z),.55,'alloy',10)
# Two real cable grips, retaining collars and ceiling plates replace the bare rods.
for x in (-80,80):
    rod(P(x,1.2,24),P(x,1.2,29),1.5,'alloy',16)
    rod(P(x,1.2,29),P(x,1.2,32),1.05,'dark',12)
    rod(P(x,1.2,32),P(x,1.2,296),.42,'alloy',12)
    rod(P(x,1.2,293),P(x,1.2,298),1.1,'alloy',12)
    box(x,1.2,299,8,6,2,'panel')
    for dx in (-2.6,2.6):rod(P(x+dx,1.2,297.8),P(x+dx,1.2,298.1),.4,'dark',8)
m.material_overrides={'face':MAT+'/face.vmat','panel':'materials/ares/interior-v1/panel.vmat','alloy':'materials/ares/interior-v1/alloy.vmat','dark':'materials/ares/interior-v1/dark.vmat','gasket':'materials/ares/ar_black.vmat'}
m.tile_overrides={p:32 for p in m.polygons}
tris=K.write_model(MODEL,RES,'observation_sign',m)

# Extract only the installed sign and its two suspension rods. Keep every other
# vertex/UV/normal/face byte unchanged in the review-only dressing mesh.
source=ROOT/'Assets/models/maps/ares/crate-v2/dressing-base.obj'
lines=source.read_text().splitlines(keepends=True)
objverts=[tuple(map(float,l.split()[1:4])) for l in lines if l.startswith('v ')]
verts=[(c,a,b) for a,b,c in objverts] # OBJ (world Y,Z,X) -> native world XYZ
kept=[];removed=[]
for line in lines:
    if line.startswith('f '):
        pts=[verts[int(t.split('/')[0])-1] for t in line.split()[1:]]
        target=all(597.3<=x<=603.1 and -97.1<=y<=97.1 and 394.9<=z<=720.1 for x,y,z in pts)
        if target:removed.append(line);continue
    kept.append(line)
assert len(removed)==30,(len(removed),'Expected 14 sign + 16 uncapped four-sided rod triangles')
trim=MODEL/'dressing_without_sign.obj'
trim.write_text(''.join(kept).replace('mtllib ares_dressing.mtl','mtllib dressing_without_sign.mtl'))
(MODEL/'dressing_without_sign.mtl').write_bytes((ROOT/'Assets/models/maps/ares/ares_dressing.mtl').read_bytes())
vmdl=(ROOT/'Assets/models/maps/ares/ares_dressing.vmdl').read_text()
vmdl=vmdl.replace('models/maps/ares/crate-v2/dressing-base.obj',RES+'/dressing_without_sign.obj')
(MODEL/'dressing_without_sign.vmdl').write_text(vmdl)
files={str(p.relative_to(STAGE)).replace('\\','/'):sha(p) for p in STAGE.rglob('*') if p.is_file()}
(OUT/'manifest.json').write_text(json.dumps(dict(files=files,triangles=tris,removed_triangles=len(removed),source=str(source.relative_to(ROOT)),source_sha256=sha(source),review_only=True),indent=2))
# Native import script uses guarded manifest copying, retaining the current scene.
template=(ROOT/'Sources/Ares/interior-v1/import_preview.cs.txt').read_text().replace('output/ares/interior-v1','output/ares/observation-sign-v1').replace('maps/ares/interior-v1/','maps/ares/observation-sign-v1/').replace('materials/ares/interior-v1/','materials/ares/observation-sign-v1/')
(Path(__file__).parent/'import.cs.txt').write_text(template)
print(json.dumps(dict(triangles=tris,removed_triangles=len(removed),staged_files=len(files))))
