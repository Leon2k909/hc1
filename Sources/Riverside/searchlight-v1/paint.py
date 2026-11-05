import numpy as np
from PIL import Image,ImageDraw,ImageFont

def build(folder):
    folder.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(70439);h,w=1024,1024
    y,x=np.mgrid[0:h,0:w];grain=rng.normal(0,1,(h,w))
    col=np.broadcast_to(np.array((106.,116.,91.)),(h,w,3)).copy()+grain[:,:,None]*1.1
    # Fine enamel orange peel and small longitudinal scratches, without broad noisy grime.
    wear=np.zeros((h,w))
    for _ in range(65):
        xx=rng.integers(0,w);yy=rng.integers(0,h);length=rng.integers(3,23)
        wear[yy:min(h,yy+length),xx]=rng.uniform(.25,.65)
    col=col*(1-wear[:,:,None])+np.array((80,72,52))*wear[:,:,None]
    Image.fromarray(np.clip(col,0,255).astype('uint8')).save(folder/'enamel_color.png')
    Image.fromarray(np.clip(156+grain*3,0,255).astype('uint8')).save(folder/'enamel_rough.png')
    dx=(np.roll(grain,1,1)-np.roll(grain,-1,1))*.011;dy=(np.roll(grain,-1,0)-np.roll(grain,1,0))*.011
    normals=np.stack((dx,dy,np.ones_like(grain)),2);normals/=np.linalg.norm(normals,axis=2)[:,:,None]
    Image.fromarray(np.clip((normals*.5+.5)*255,0,255).astype('uint8')).save(folder/'enamel_normal.png')
    Image.new('RGB',(8,8),(240,240,240)).save(folder/'hardware_color.png')
    im=Image.new('RGB',(1024,512),(36,41,35));d=ImageDraw.Draw(im)
    def f(s):return ImageFont.truetype('C:/Windows/Fonts/bahnschrift.ttf',s)
    d.rectangle((8,8,1015,503),outline=(164,173,146),width=5)
    d.text((42,28),'PARK WATCH',font=f(90),fill=(214,216,192))
    d.text((42,145),'SL-1500',font=f(116),fill=(219,222,201))
    d.line((44,290,980,290),fill=(152,163,134),width=3)
    d.text((42,318),'120 V  /  1.5 kW',font=f(53),fill=(180,192,157))
    d.text((42,414),'HOT SURFACE  -  DO NOT COVER',font=f(39),fill=(206,175,94))
    im.save(folder/'plate_color.png')
    for name,tint,metal,rough,color in (
        ('enamel',(1,1,1),.12,1,'enamel_color.png'),
        ('alloy',(.55,.58,.54),.82,.57,'hardware_color.png'),
        ('rubber',(.045,.052,.041),0,1.2,'hardware_color.png'),
        ('brass',(.47,.33,.14),.7,.7,'hardware_color.png'),
        ('plate',(1,1,1),.35,.85,'plate_color.png')):
        (folder/(name+'.vmat')).write_text(material(color,tint,metal,rough))

def material(color,tint,metal,rough):
    prefix='materials/riverside/searchlight-v1/'
    return f'''"Layer0"
{{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 g_flMetalness "{metal}"
 g_flRoughnessScaleFactor "{rough}"
 TextureColor "{prefix+color}"
 TextureNormal "{prefix}enamel_normal.png"
 TextureRoughness "{prefix}enamel_rough.png"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"
 g_flModelTintAmount "1"
}}
'''
