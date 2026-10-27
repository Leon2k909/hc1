"""Rear-yard FB/041 cargo-truck reference details and private PBR finishes."""
import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import forestbase_truck as T

RESOURCE='materials/forestbase/truck041'

def details(out,api,block,rod,face,bolt,handle,ring,cloth):
    # Split rear canvas curtains with hanging gathers and a folded centre seam.
    def curtain(y,v):
        height=120+10*math.sqrt(max(0,1-(y/44)**2))
        z=68+(height-68)*v
        fold=(.9+1.2*math.sin(y*.33+v*2)**2)*math.sin(math.pi*v)
        fold+=.6*math.sin(y*.8-v*5)*math.sin(math.pi*v)
        return np.array((-139.65-fold,y,z))
    for ya,yb in ((-44,-.55),(.55,44)):
        for a in range(28):
            for b in range(36):
                coords=[(a/28,b/36),((a+1)/28,b/36),((a+1)/28,(b+1)/36),(a/28,(b+1)/36)]
                pts=[curtain(ya+(yb-ya)*s,v) for s,v in coords]
                ns=[]
                for s,v in coords:
                    y=ya+(yb-ya)*s
                    normal=np.cross(curtain(y+.001,v)-curtain(y-.001,v),curtain(y,v+.0001)-curtain(y,v-.0001))
                    ns.append(-normal/np.linalg.norm(normal))
                face(pts,'canvas',normal=(-1,0,0),uv=[((p[1]+44)/88,v) for p,(_,v) in zip(pts,coords)],normals=ns)
    rod((-141,-.1,68),(-141,-.1,128),.42,'webbing')
    for y in np.arange(-41,44,9):
        ring((-141.8,y,69),.8,(-1,0,0),width=.22)
        rod((-142,y,68),(-142,y+1.7,64),.25,'webbing')
    # Rear gate: pressed ribs, hinges, locking rods and corner catches.
    block((-142,-44,49),(-140,44,68),r=.35)
    for zz in (52,58,64):block((-143,-43,zz),(-142.1,43,zz+2.6),r=.25)
    for yy in (-43,-17,17,43):
        block((-144,yy-1.3,48),(-142.7,yy+1.3,68),'metal',.3)
        for zz in (51,65):bolt((-144.4,yy,zz),(-1,0,0),.5)
    for yy in (-30,30):
        rod((-144.6,yy,50),(-144.6,yy,67),.5)
        handle((-145.1,yy-2,57),(-145.1,yy+2,57),up=(-.8,0,0),r=.4)
        rod((-143,yy-4,49),(-143,yy+4,49),.85)
    # Lower rear lamp clusters sit on substantial housings.
    for yy in (-35,35):
        block((-145,yy-8,36),(-139,yy+8,46),'metal',.6)
        for ya,yb,p in ((yy-7,yy-2,'red'),(yy-1,yy+3,'amber'),(yy+4,yy+7,'lamp')):
            block((-145.3,ya,38),(-145.05,yb,44),p,.2)
        block((-143,yy-3,69),(-141,yy+3,72),'amber',.3)
    block((-150,-48,23),(-143,48,29),'metal',.65)
    for yy in (-25,25):
        rod((-147,yy,24),(-147,yy,17),1.05)
        handle((-147,yy-2.5,18),(-147,yy+2.5,18),up=(-3,0,0),r=.8)
    handle((-145,-16,32),(-145,16,32),up=(-6,0,0),r=1)
    # Folded rear fenders and heavy rubber mudflaps.
    for side in (-1,1):
        for x in (-104,-45):
            outer=[(-28,2),(-28,14),(-16,29),(16,29),(28,14),(28,2)]
            inner=[(-24,3),(-24,12),(-14,25),(14,25),(24,12),(24,3)]
            for k in range(5):
                face([(x+xx,side*59,22+zz) for xx,zz in (outer[k],outer[k+1],inner[k+1],inner[k])],normal=(0,side,0))
                face([(x+xx,yy,22+zz) for (xx,zz),yy in ((outer[k],side*43),(outer[k+1],side*43),(outer[k+1],side*59),(outer[k],side*59))],normal=(0,0,1))
            block((x-29,min(side*43,side*57),9),(x-27,max(side*43,side*57),34),'rubber',.35)
            for yy in (side*46,side*54):bolt((x-29.3,yy,32),(-1,0,0),.45)
        for x in (-104,-45,93):
            for angle in np.linspace(0,math.tau,10,endpoint=False):
                bolt((x+7.2*math.cos(angle),side*53.2,22+7.2*math.sin(angle)),(0,side,0),.7)
        for x in (-119,-64,-11):
            block((x,min(side*46,side*47),47),(x+5,max(side*46,side*47),50),'amber',.25)
        # Buckles and draw catches continue down to the drop-side hinges.
        for x in (-133,-92,-51,-10,35):
            for z in (52,64):
                block((x-1,min(side*46,side*47),z),(x+1,max(side*46,side*47),z+4),'metal',.25)
                bolt((x,side*47.3,z+2),(0,side,0),.35)
            for y in (side*45.8,):
                rod((x,y,69),(x,y,56),.42,'webbing')
        for x in (-130,-87,-44):
            for z in (51,65):bolt((x,side*46.5,z),(0,side,0),.5)

def materials(out,source):
    """Private materials leave the three existing FB/027 trucks untouched."""
    out=Path(out);T.materials(out)
    for p in out.glob('*.vmat'):p.write_text(p.read_text().replace(T.RESOURCE,RESOURCE))
    im=Image.open(source).convert('RGB').resize((2048,2048),Image.Resampling.LANCZOS)
    # The generated scan supplies fine textile grain; geometry supplies large folds.
    # Filter subpixel weave contrast to avoid a sparkling textile in motion.
    im=im.filter(ImageFilter.GaussianBlur(.75))
    a=np.asarray(im,float);low=np.asarray(im.filter(ImageFilter.GaussianBlur(6)),float)
    a=low+(a-low)*.38
    gray=np.asarray(im.convert('L'),float)
    smooth=np.asarray(im.convert('L').filter(ImageFilter.GaussianBlur(5)),float)
    grain=gray-smooth;dy,dx=np.gradient(grain*.008)
    normal=np.stack((-dx,dy,np.ones_like(dx)),axis=-1);normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    # A slightly faded olive tint keeps the cloth distinct from the steelwork.
    a=np.clip(a*np.array((.94,.98,.88))[None,None,:],0,255)
    Image.fromarray(a.astype('uint8')).save(out/'canvas_color.png',compress_level=3)
    Image.fromarray(np.clip((normal*.5+.5)*255,0,255).astype('uint8')).save(out/'canvas_normal.png',compress_level=3)
    Image.fromarray(np.clip(218+grain*.15,200,235).astype('uint8')).convert('RGB').save(out/'canvas_rough.png')
    # Wheel metal and dusty rubber are lighter than the previous near-black finish.
    for name,scale in [('paint',(.79,.82,.77)),('rubber',(1.28,1.20,1.03))]:
        p=out/(name+'_color.png');arr=np.asarray(Image.open(p).convert('RGB'),float)
        Image.fromarray(np.clip(arr*np.array(scale),0,255).astype('uint8')).save(p,compress_level=3)
    # Exact marking from the new reference.
    stencil=Image.new('RGBA',(512,512));d=ImageDraw.Draw(stencil)
    for y in (55,108):d.polygon([(174,y+62),(256,y),(338,y+62),(338,y+89),(256,y+29),(174,y+89)],fill=(211,208,181,245))
    font=ImageFont.truetype('C:/Windows/Fonts/consolab.ttf',64)
    d.text((45,288),'FB / 041',font=font,fill=(211,208,181,245))
    a=np.array(stencil);rng=np.random.default_rng(41041);a[:,:,3][rng.random((512,512))<.045]=0
    Image.fromarray(a[:,:,:3]).save(out/'stencil_color.png');Image.fromarray(a[:,:,3]).save(out/'stencil_alpha.png')
