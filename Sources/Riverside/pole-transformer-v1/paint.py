from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont

def build(folder):
    folder.mkdir(parents=True,exist_ok=True);rng=np.random.default_rng(40321)
    H,W=1024,2048;y,x=np.mgrid[0:H,0:W];u=x/W;v=y/H
    grain=rng.normal(0,1,(H,W))
    stripes=np.zeros((H,W))
    for k in range(28):
        at=rng.uniform();width=rng.uniform(.0008,.0035);dist=np.minimum(np.abs(u-at),1-np.abs(u-at))
        trail=np.exp(-(dist/width)**2)*np.clip((v-rng.uniform(0,.18))/.45,0,1)*np.exp(-v*2.2)
        stripes+=trail*rng.uniform(0.4,1.)
    base=np.array((126,143,134),float)
    col=np.broadcast_to(base,(H,W,3)).copy()+grain[:,:,None]*1.1
    col-=stripes[:,:,None]*np.array((9,13,12))
    # Sparse oxidised traces confined to the rolled lower edge, without cloudy mottling.
    wear=np.exp(-((v-.965)/.018)**2)*(np.sin(u*math_tau()*19)*.5+.5)**7
    col=col*(1-wear[:,:,None]*.35)+np.array((114,76,48))*wear[:,:,None]*.35
    Image.fromarray(np.clip(col,0,255).astype('uint8')).save(folder/'tank_color.png')
    Image.fromarray(np.clip(base+grain[:1024,:1024,None]*1.1,0,255).astype('uint8')).save(folder/'lid_color.png')
    Image.fromarray(np.clip(164+grain*3+stripes*7,0,255).astype('uint8')).save(folder/'tank_rough.png')
    dx=(np.roll(grain,1,1)-np.roll(grain,-1,1))*.014;dy=(np.roll(grain,-1,0)-np.roll(grain,1,0))*.014
    normals=np.stack((dx,dy,np.ones_like(grain)),axis=2);normals/=np.linalg.norm(normals,axis=2)[:,:,None]
    Image.fromarray(np.clip((normals*.5+.5)*255,0,255).astype('uint8')).save(folder/'tank_normal.png')
    Image.new('RGB',(8,8),(242,242,242)).save(folder/'hardware_color.png')
    im=Image.new('RGB',(1024,640),(213,214,190));d=ImageDraw.Draw(im)
    def f(s):return ImageFont.truetype('C:/Windows/Fonts/bahnschrift.ttf',s)
    d.rectangle((6,6,1017,633),outline=(42,48,38),width=7);d.rectangle((26,26,997,135),fill=(43,57,47))
    d.text((50,45),'COUNTY ELECTRIC',font=f(69),fill=(223,225,207))
    d.text((46,167),'TX-25',font=f(124),fill=(36,44,36));d.text((48,310),'DISTRIBUTION UNIT',font=f(50),fill=(42,49,39))
    d.line((48,386,975,386),fill=(70,75,60),width=4);d.text((48,415),'25 kVA   /   OIL FILLED',font=f(45),fill=(42,49,39))
    d.text((48,510),'DANGER  /  HIGH VOLTAGE',font=f(45),fill=(65,47,30))
    d.polygon([(826,167),(964,357),(686,357)],fill=(207,166,44),outline=(43,42,30),width=8)
    d.polygon([(841,194),(776,279),(824,273),(797,329),(894,247),(843,255)],fill=(34,37,28))
    im.save(folder/'label_color.png')
    coats={'coat':('tank_color.png',(1,1,1),.03,1),'lid':('lid_color.png',(.96,.98,.95),.08,.93)}
    constants={'alloy':((.42,.47,.43),.72,.42),'ceramic':((.64,.57,.43),0,.30),'dark':((.045,.055,.049),.02,.8),'brass':((.44,.30,.10),.68,.5)}
    for name,(color,tint,metal,rough) in coats.items():
        (folder/f'{name}.vmat').write_text(material(color,tint,metal,rough,'tank_normal.png','tank_rough.png'))
    for name,(tint,metal,rough) in constants.items():
        (folder/f'{name}.vmat').write_text(material('hardware_color.png',tint,metal,rough,'tank_normal.png','tank_rough.png'))
    (folder/'label.vmat').write_text(material('label_color.png',(1,1,1),.05,.8,'materials/default/default_normal.tga','materials/default/default_rough.tga'))

def math_tau():return 2*np.pi
def material(color,tint,metal,rough,normal,roughmap):
    def path(s):return s if s.startswith('materials/') else 'materials/riverside/pole-transformer-v1/'+s
    return f'''"Layer0"
{{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 g_flMetalness "{metal}"
 g_flRoughnessScaleFactor "{rough}"
 TextureColor "{path(color)}"
 TextureNormal "{path(normal)}"
 TextureRoughness "{path(roughmap)}"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"
 g_flModelTintAmount "1"
}}
'''
