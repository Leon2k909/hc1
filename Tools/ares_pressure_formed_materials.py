"""Deterministic PBR paint, printed cassettes and instruments for formed Ares doors."""
from pathlib import Path
import math
import numpy as np
from scipy.ndimage import gaussian_filter
from PIL import Image,ImageDraw,ImageFont
from ares_pressure_formed import PREFIX,NAMES,cassette_layout

COLOURS={'body':(79,94,101),'panel':(196,190,172),'frame':(55,66,73),
         'steel':(169,176,174),'rubber':(22,25,23),'accent':(188,83,28),'dark':(35,41,43),'kick':(38,44,46)}
ROUGH={'body':.43,'panel':.40,'frame':.45,'steel':.31,'rubber':.78,'accent':.43,'dark':.48,'kick':.45}


def font(size,bold=False):
    return ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf',max(6,int(size)))


def surfaces(out):
    rng=np.random.default_rng(261026031);n=2048
    y,x=np.mgrid[:n,:n].astype(np.float32)/(n-1)
    noise=rng.normal(size=(n,n)).astype(np.float32)
    fine=gaussian_filter(noise,.65);fine/=fine.std()
    grain=gaussian_filter(noise,(.5,9));grain/=grain.std()
    slow=gaussian_filter(noise,19);slow/=slow.std()
    edge=np.minimum.reduce((x,1-x,y,1-y))
    chips=(edge<(.0013+.0009*np.clip(slow,0,2)))&(fine>.9)
    dust=np.exp(-(1-y)/.055)*np.clip(.55+.13*slow,0,1)
    rubbed=np.exp(-((y-.73)/.14)**2)*np.maximum(grain-2.0,0)*.011
    height=.018*fine+.004*grain
    for name,base in COLOURS.items():
        variation=.005*fine+.006*slow+(.016 if name=='steel' else .004)*grain
        rgb=np.asarray(base)[None,None,:]*(1+variation[...,None])
        r=np.clip(ROUGH[name]+.011*fine+.013*slow+rubbed,.10,.92)
        if name not in ('steel','rubber'):
            rgb=rgb*(1-dust[...,None]*.075)+np.array((102,84,62))*dust[...,None]*.075
            rgb=np.where(chips[...,None],np.array((126,133,133)),rgb)
            rgb+=rubbed[...,None]*180
            r=np.where(chips,.31,r)
        image=Image.fromarray(np.uint8(np.clip(rgb,0,255)))
        if name in ('body','kick','frame'):
            d=ImageDraw.Draw(image)
            for _ in range(170 if name=='body' else 100):
                sx=float(rng.uniform(.04,.96)*n);sy=float(rng.uniform(.58,.98)*n)
                length=float(rng.uniform(2,27));angle=float(rng.uniform(-.38,.38))
                value=np.array(base)+(rng.uniform(9,25) if rng.random()<.60 else -rng.uniform(5,12))
                d.line((sx,sy,sx+length*math.cos(angle),sy+length*math.sin(angle)),
                    fill=tuple(int(v) for v in np.clip(value,0,255)),width=1)
        image.save(out/f'{name}_color.png')
        Image.fromarray(np.uint8(r*255)).save(out/f'{name}_rough.png')
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))*.75
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))*.75
    normal=np.stack((-dx,dy,np.ones_like(dx)),axis=-1);normal/=np.linalg.norm(normal,axis=-1)[...,None]
    Image.fromarray(np.uint8(np.clip(normal*.5+.5,0,1)*255)).save(out/'paint_normal.png')
    # Millimetre dents and scuffs in the replaceable lower plate, rather than
    # adding broad noise to every material or changing its collision silhouette.
    dent=np.zeros((n,n),np.float32)
    for cx,cy,sx,sy,depth in ((.34,.46,.095,.14,.13),(.73,.61,.065,.12,.09)):
        dent-=depth*np.exp(-.5*((x-cx)/sx)**2-.5*((y-cy)/sy)**2)
    gy,gx=np.gradient(dent,20/(n-1),150/(n-1))
    kn=np.stack((-gx,gy,np.ones_like(gx)),axis=-1);kn/=np.linalg.norm(kn,axis=-1)[...,None]
    Image.fromarray(np.uint8(np.clip(kn*.5+.5,0,1)*255)).save(out/'kick_normal.png')
    Image.new('RGB',(16,16),(128,128,255)).save(out/'flat_normal.png')
    Image.new('L',(16,16),160).save(out/'label_rough.png')


def cassettes(out):
    colour=Image.new('RGB',(2048,2048),COLOURS['panel'])
    rough=Image.new('L',(2048,2048),round(ROUGH['panel']*255))
    ao=Image.new('L',(2048,2048),255)
    rng=np.random.default_rng(26102606)
    for unit,(width,height) in enumerate(((320,200),(180,180),(180,180))):
        for side in (-1,1):
            l=cassette_layout(width,height,side);w=round(l['w']*10);h=round(l['h']*10)
            yy,xx=np.mgrid[:h,:w].astype(np.float32)
            u=xx/(w-1);v=yy/(h-1)
            fine=rng.normal(size=(h,w)).astype(np.float32)
            fine=gaussian_filter(fine,.65);fine/=fine.std()
            c=np.asarray(COLOURS['panel'])[None,None,:]*(1+.003*fine[...,None])
            physical_u=(u-.008)/.984;physical_v=(v-.012)/.976
            boundary=np.minimum.reduce((physical_u,1-physical_u,physical_v,1-physical_v))
            chip=(boundary<.0019)&(fine>1.05)
            c=np.where(chip[...,None],np.array((129,133,127)),c)
            image=Image.fromarray(np.uint8(np.clip(c,0,255)));d=ImageDraw.Draw(image)
            ink=(35,41,43);orange=(182,87,29)
            if side<0:
                f=w*.078;px=w*(.11 if unit==0 else .18);py=h*.21
                d.text((px,py),'ARES',font=font(f,True),fill=ink)
                d.line((px,py+f*1.03,px+w*.245,py+f*1.03),fill=orange,width=max(2,round(f*.065)))
                d.text((px,py+f*1.25),('AIRLOCK 07','AIRLOCK 03','AIRLOCK 07')[unit],font=font(f*.40,True),fill=ink)
                # Small, shallow press-mark above the printed equipment identity.
                d.line((w*.10,h*.095,w*.30,h*.095,w*.32,h*.13),fill=(163,159,145),width=max(1,round(w*.001)))
            else:
                f=w*(.035 if unit==0 else .029);px=w*(.66 if unit==0 else .62);py=h*.26
                d.text((px,py),'PRESSURE LOCK',font=font(f,True),fill=ink)
                d.line((px+w*.14,py+f*1.3,px+w*.285,py+f*1.3),fill=orange,width=max(2,round(f*.12)))
            px=l['lo']+physical_u*l['w'];pz=l['high']-physical_v*l['h'];ambient=np.ones((h,w),np.float32)
            for groove in l['grooves']:
                gx=(groove[:,0].min()+groove[:,0].max())/2;r=(groove[:,0].max()-groove[:,0].min())/2
                z0,z1=groove[:,1].min()+r,groove[:,1].max()-r
                distance=np.sqrt((px-gx)**2+(pz-np.clip(pz,z0,z1))**2)-r
                ambient*=1-.17*np.exp(-np.maximum(distance,0)/.55)
            dx=np.abs(px-l['hx'])-l['hw']/2;dz=np.abs(pz-l['hz'])-l['hh']/2
            distance=np.sqrt(np.maximum(dx,0)**2+np.maximum(dz,0)**2)+np.minimum(np.maximum(dx,dz),0)
            ambient*=1-.18*np.exp(-np.maximum(distance,0)/.45)
            tile=unit*2+int(side>0);xy=(tile%2*1024,tile//2*512)
            colour.paste(image.resize((1024,512),Image.Resampling.LANCZOS),xy)
            rough.paste(Image.fromarray(np.uint8(np.clip(ROUGH['panel']+.008*fine,.2,.8)*255)).resize((1024,512),Image.Resampling.LANCZOS),xy)
            ao.paste(Image.fromarray(np.uint8(np.clip(ambient,0,1)*255)).resize((1024,512),Image.Resampling.LANCZOS),xy)
    colour.save(out/'cassette_color.png');rough.save(out/'cassette_rough.png');ao.save(out/'cassette_ao.png')


def graphics(out):
    atlas=Image.new('RGB',(2048,2048),(30,37,40))
    for tile in (4,5,8):
        aspect={4:4.65,5:3.10,8:1.}[tile];w=round(512*aspect);h=512
        image=Image.new('RGB',(w,h),(30,37,40));d=ImageDraw.Draw(image)
        if tile==4:
            d.text((w/2,190),'MANUAL RELEASE',font=font(148,True),fill=(205,211,203),anchor='mm')
            d.text((w/2,362),'ISOLATE BEFORE OPERATING',font=font(65),fill=(153,168,169),anchor='mm')
        elif tile==5:
            yellow=(221,155,42);ink=(24,29,29);d.rectangle((0,0,w,h),fill=yellow)
            d.polygon(((65,390),(235,80),(405,390)),fill=ink)
            d.text((235,289),'!',font=font(205,True),fill=yellow,anchor='mm')
            d.text((w*.64,200),'CAUTION',font=font(175,True),fill=ink,anchor='mm')
            d.text((w*.64,372),'KEEP SEAL CLEAR',font=font(60,True),fill=ink,anchor='mm')
        else:
            d.rectangle((0,0,w,h),fill=(218,217,199));ink=(31,38,37)
            d.ellipse((16,16,496,496),outline=ink,width=3)
            for i in range(51):
                a=math.radians(135+i*5.4);r=218;inner=r-(26 if i%5==0 else 11)
                d.line((256+r*math.cos(a),256+r*math.sin(a),256+inner*math.cos(a),256+inner*math.sin(a)),fill=ink,width=4 if i%5==0 else 2)
                if i%10==0:
                    d.text((256+159*math.cos(a),256+159*math.sin(a)),str(i*2),font=font(25),fill=ink,anchor='mm')
            d.text((256,321),'DIFFERENTIAL',font=font(24,True),fill=ink,anchor='mm')
            d.text((256,356),'kPa',font=font(28),fill=ink,anchor='mm')
            d.text((256,398),'ARES  /  DP-204',font=font(17),fill=(72,77,69),anchor='mm')
        atlas.paste(image.resize((512,512),Image.Resampling.LANCZOS),(tile%4*512,tile//4*512))
    atlas.save(out/'labels_color.png')
    image=Image.new('RGB',(768,1152),(8,17,17));d=ImageDraw.Draw(image);ink=(128,182,130)
    for y,text,size in ((95,'ARES / AIRLOCK',45),(260,'PRESSURE LOCK',45),(490,'SEALED',102),(800,'INTERLOCK ACTIVE',40),(1030,'LOCAL CONTROL',35)):
        d.text((384,y),text,font=font(size,True),fill=ink,anchor='mm')
    d.line((70,160,698,160),fill=(69,112,80),width=3)
    d.rounded_rectangle((70,711,698,890),radius=12,outline=(69,112,80),width=4)
    image.resize((512,1024),Image.Resampling.LANCZOS).save(out/'display_color.png')
    n=512;yy,xx=np.mgrid[:n,:n];stripe=((xx+yy)//64)%2
    rgb=np.where(stripe[...,None]>0,np.array((209,147,38)),np.array((27,31,31))).astype(np.float32)
    rng=np.random.default_rng(26102699);scratch=(rng.random((n,n))>.987)
    rgb=np.where(scratch[...,None],np.array((112,116,111)),rgb)
    Image.fromarray(np.uint8(rgb)).save(out/'hazard_color.png')


def write_materials(directory):
    out=Path(directory);out.mkdir(parents=True,exist_ok=True);surfaces(out);cassettes(out);graphics(out)
    for name in NAMES:
        if name=='glass':
            text=('"Layer0"\n{\n    shader "shaders/glass.shader"\n'
                  '    F_GLASS_QUALITY "2"\n    F_DO_NOT_CAST_SHADOWS "1"\n    g_flTintColor "[1 1 1 0]"\n'
                  '    TextureColor "[0.96 0.98 0.98 0]"\n    TextureRoughness "[0.10 0.10 0.10 0]"\n'
                  '    TextureMetalness "[0 0 0 0]"\n    TextureTranslucency "[1 1 1 0]"\n'
                  f'    TextureNormal "{PREFIX}/flat_normal.png"\n'
                  '    g_flRefractionStrength "1.001"\n    AlbedoAbsorption "0.06"\n}\n')
        else:
            textured=name not in ('red','green');color=f'{PREFIX}/{name}_color.png' if textured else 'materials/default/default_color.tga'
            rough=f'{PREFIX}/{name}_rough.png' if name in COLOURS or name=='cassette' else f'{PREFIX}/label_rough.png'
            normal=f'{PREFIX}/kick_normal.png' if name=='kick' else f'{PREFIX}/paint_normal.png' if name in ('body','panel','frame','accent','dark','cassette') else f'{PREFIX}/flat_normal.png'
            ao=f'{PREFIX}/cassette_ao.png' if name=='cassette' else 'materials/default/default_ao.tga'
            metal=.92 if name=='steel' else 0.
            tint={'red':(.55,.035,.018),'green':(.055,.31,.11)}.get(name,(1,1,1))
            emission=('    F_SELF_ILLUM "1"\n    TextureSelfIllumMask "[1 1 1 0]"\n'
                      f'    g_flSelfIllumBrightness "{.35 if name=="display" else .12}"\n'
                      '    g_flSelfIllumAlbedoFactor "1"\n    g_vSelfIllumTint "[1 1 1 0]"\n') if name in ('display','green') else ''
            text=('"Layer0"\n{\n    shader "shaders/complex.shader"\n'
                f'    F_SPECULAR "{0 if name in ("labels","display") else 1}"\n'+emission+
                f'    g_flMetalness "{metal}"\n    g_flRoughnessScaleFactor "1"\n'
                f'    TextureColor "{color}"\n    TextureNormal "{normal}"\n    TextureRoughness "{rough}"\n'
                f'    TextureAmbientOcclusion "{ao}"\n    g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"\n'
                '    g_flModelTintAmount "1"\n}\n')
        (out/f'{name}.vmat').write_text('// Tools/ares_pressure_formed_materials.py\n'+text)
