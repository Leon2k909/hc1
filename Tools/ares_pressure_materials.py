"""Private coated metal, seals and authored equipment graphics for Ares doors."""
from pathlib import Path
import math
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image,ImageDraw,ImageFont
from ares_pressure_door import PREFIX,NAMES


def font(size,bold=False):
    return ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf',size)


def graphics(out):
    atlas=Image.new('RGB',(2048,2048),(34,42,46))
    for tile in range(16):
        aspect={0:4.9,1:4.9,2:4.9,3:3.5,4:3.85,5:4.67,10:3.,11:1.7}.get(tile,1.)
        h=512;w=round(h*aspect);im=Image.new('RGB',(w,h),(34,42,46));d=ImageDraw.Draw(im)
        white=(220,225,218);orange=(211,145,63);light=(151,166,168)
        def text(x,y,s,size,colour=white,bold=False):d.text((x,y),s,font=font(size,bold),fill=colour,anchor='mm')
        if tile in (0,1,2):
            d.rectangle((0,0,w-1,h-1),fill=(43,54,59));d.rectangle((18,18,w-18,h-18),outline=(126,140,139),width=5)
            text(w*.23,180,'ARES',175,white,True);text(w*.24,345,'ATMOSPHERIC SYSTEMS',57,light)
            d.line((w*.45,80,w*.45,420),fill=orange,width=8)
            text(w*.72,188,('CARGO 07','AIRLOCK 03','AIRLOCK 07')[tile],121,white,True)
            text(w*.72,350,'PRESSURE BOUNDARY  /  CLASS IV',55,light)
        elif tile==4:
            text(w/2,173,'MANUAL RELEASE',111,white,True)
            text(w/2,342,'ISOLATE CHAMBER BEFORE OPERATING',52,light)
            d.line((60,438,w-60,438),fill=orange,width=9)
        elif tile==5:
            d.rectangle((0,0,w,h),fill=orange)
            d.polygon(((80,390),(250,80),(420,390)),fill=(28,31,30))
            d.text((250,292),'!',font=font(200,True),fill=orange,anchor='mm')
            text(w*.63,205,'STAND CLEAR',159,(28,31,30),True)
            text(w*.63,379,'KEEP SEAL AND THRESHOLD CLEAN',55,(28,31,30))
        elif tile==8:
            d.rectangle((0,0,511,511),fill=(219,219,201))
            d.ellipse((20,20,492,492),outline=(38,48,48),width=4)
            for i in range(41):
                angle=math.radians(135+i*6.75);radius=212
                a=(256+radius*math.cos(angle),256+radius*math.sin(angle))
                b=(256+(radius-(27 if i%5==0 else 12))*math.cos(angle),256+(radius-(27 if i%5==0 else 12))*math.sin(angle))
                d.line((*a,*b),fill=(35,45,46),width=4 if i%5==0 else 2)
                if i%10==0:
                    p=(256+155*math.cos(angle),256+155*math.sin(angle))
                    d.text(p,str(-100+i*5),font=font(26,True),fill=(35,45,46),anchor='mm')
            text(256,309,'DIFFERENTIAL',26,(35,45,46),True)
            text(256,347,'kPa',30,(35,45,46));text(256,391,'ARES  /  DP-204',18,(65,70,64))
        elif tile==10:
            text(w/2,147,'ACCESS  /  PRESSURE',87,light,True)
            text(w/2,349,'LOCAL CONTROL',91,white,True)
        elif tile==11:
            d.rectangle((0,0,w,h),fill=(187,76,43));d.polygon(((w*.35,0),(w*.56,0),(w*.80,h),(w*.59,h)),fill=(220,215,187))
        else:
            text(w/2,h/2,'ARES  /  SERVICE',48,light,True)
        if tile!=8:
            # Antialias at the atlas's true pixel footprint. Wide equipment
            # graphics are precompensated for their real rectangular UV aspect.
            im=im.resize((512,512),Image.Resampling.LANCZOS)
        atlas.paste(im,((tile%4)*512,(tile//4)*512))
    atlas.save(out/'labels_color.png')
    display=Image.new('RGB',(512,512),(8,22,25));d=ImageDraw.Draw(display)
    cyan=(135,204,198);green=(111,186,129);white=(187,218,210)
    def t(x,y,s,size,c=cyan,bold=False):d.text((x,y),s,font=font(size,bold),fill=c,anchor='mm')
    t(256,46,'ARES // AIRLOCK',32,white,True);d.line((30,78,482,78),fill=cyan,width=2)
    t(256,128,'PRESSURE LOCK',26,cyan);t(256,207,'SEALED',68,green,True)
    d.rounded_rectangle((48,267,464,343),radius=7,outline=green,width=3)
    t(256,306,'INTERLOCK ACTIVE',29,green,True)
    t(256,394,'CHAMBER   /   NORMAL',25,white)
    t(256,463,'LOCAL ACCESS CONTROL',23,cyan)
    display.save(out/'display_color.png')
    n=256;y,x=np.mgrid[:n,:n];stripe=((x+y)//32)%2
    colour=np.where(stripe[...,None]>0,np.array((190,136,48)),np.array((29,34,35)))
    Image.fromarray(np.uint8(colour)).save(out/'hazard_color.png')


def surfaces(out):
    rng=np.random.default_rng(611720);n=2048
    y,x=np.mgrid[:n,:n].astype(np.float32)/(n-1)
    noise=rng.normal(size=(n,n)).astype(np.float32)
    fine=gaussian_filter(noise,1.0);fine/=fine.std()
    broad=gaussian_filter(noise,45);broad/=broad.std()
    grain=gaussian_filter(noise,(.5,12));grain/=grain.std()
    distance=np.minimum.reduce((x,1-x,y,1-y))
    edge=(distance<(.0015+.0012*np.clip(broad,-1,2))) & (fine>.8)
    lower=np.exp(-(1-y)/.085)*np.clip(.55+.16*broad,0,1)
    scuff=np.clip((grain-1.7)*.020,0,.055)*np.exp(-(1-y)/.16)
    for name,base in {'body':(81,100,111),'panel':(173,180,177),'frame':(52,63,68),
                      'steel':(157,165,168),'rubber':(24,27,26),'accent':(169,96,41),
                      'dark':(27,34,39)}.items():
        strength=.022 if name=='steel' else .010
        rgb=np.asarray(base)[None,None,:]*(1+strength*grain[...,None]+.018*broad[...,None])
        if name in ('body','panel','frame','accent'):
            rgb=rgb*(1-lower[...,None]*.085)+np.array((101,77,55))*lower[...,None]*.085
            rgb=np.where(edge[...,None],np.array((91,97,98)),rgb)
            rgb+=scuff[...,None]*75
        Image.fromarray(np.uint8(np.clip(rgb,0,255))).save(out/f'{name}_color.png')
        rough={'body':.45,'panel':.43,'frame':.49,'steel':.28,'rubber':.78,'accent':.47,'dark':.40}[name]
        r=np.clip(rough+.018*fine+.025*broad+lower*.06,.1,.9)
        Image.fromarray(np.uint8(r*255)).save(out/f'{name}_rough.png')
    h=.0030*fine+.001*grain
    dx=(np.roll(h,-1,1)-np.roll(h,1,1))*.7;dy=(np.roll(h,-1,0)-np.roll(h,1,0))*.7
    normal=np.stack((-dx,dy,np.ones_like(dx)),axis=-1);normal/=np.linalg.norm(normal,axis=-1)[...,None]
    Image.fromarray(np.uint8(np.clip(normal*.5+.5,0,1)*255)).save(out/'paint_normal.png')
    Image.new('RGB',(16,16),(128,128,255)).save(out/'flat_normal.png')
    Image.new('L',(16,16),175).save(out/'label_rough.png')


def write_materials(directory):
    out=Path(directory);out.mkdir(parents=True,exist_ok=True);surfaces(out);graphics(out)
    for name in NAMES:
        if name=='glass':
            text=('// Tools/ares_pressure_materials.py\n"Layer0"\n{\n    shader "shaders/glass.shader"\n'
                  '    F_GLASS_QUALITY "2"\n    F_DO_NOT_CAST_SHADOWS "1"\n    g_flTintColor "[1 1 1 0]"\n'
                  '    TextureColor "[0.95 0.98 0.98 0]"\n    TextureRoughness "[0.13 0.13 0.13 0]"\n'
                  '    TextureMetalness "[0 0 0 0]"\n    TextureTranslucency "[1 1 1 0]"\n'
                  f'    TextureNormal "{PREFIX}/flat_normal.png"\n'
                  '    g_flRefractionStrength "1.002"\n    AlbedoAbsorption "0.12"\n}\n')
        else:
            textured=name in ('body','panel','frame','steel','rubber','accent','dark','labels','display','hazard')
            color=f'{PREFIX}/{name}_color.png' if textured else 'materials/default/default_color.tga'
            normal=f'{PREFIX}/paint_normal.png' if name in ('body','panel','frame','accent','dark') else f'{PREFIX}/flat_normal.png'
            rough=f'{PREFIX}/{name}_rough.png' if name in ('body','panel','frame','steel','rubber','accent','dark') else f'{PREFIX}/label_rough.png'
            tint={'red':(.49,.035,.025),'green':(.04,.25,.10)}.get(name,(1,1,1))
            metal=.90 if name=='steel' else .12 if name in ('frame','dark') else 0
            emission=('    F_SELF_ILLUM "1"\n    TextureSelfIllumMask "[1 1 1 0]"\n'
                      f'    g_flSelfIllumBrightness "{.38 if name=="display" else .14}"\n'
                      '    g_flSelfIllumAlbedoFactor "1"\n    g_vSelfIllumTint "[1 1 1 0]"\n') if name in ('display','green') else ''
            text=('// Tools/ares_pressure_materials.py\n"Layer0"\n{\n    shader "shaders/complex.shader"\n'
                  f'    F_SPECULAR "{0 if name in ("labels","display") else 1}"\n'+emission+
                  f'    g_flMetalness "{metal}"\n    g_flRoughnessScaleFactor "1"\n'
                  f'    TextureColor "{color}"\n    TextureNormal "{normal}"\n    TextureRoughness "{rough}"\n'
                  '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n'
                  f'    g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"\n    g_flModelTintAmount "1"\n}}\n')
        (out/f'{name}.vmat').write_text(text)
