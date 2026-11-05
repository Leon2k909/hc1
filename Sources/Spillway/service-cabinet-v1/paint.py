"""Quiet powder coating and a readable equipment plate; no baked illumination."""
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont

def build(folder):
    folder.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(7401)
    noise=rng.normal(0,1,(1024,1024))
    color=np.clip(242+noise[...,None]*1.25,0,255).astype(np.uint8)
    color=np.repeat(color,3,axis=2)
    Image.fromarray(color).save(folder/'coat_color.png')
    rough=np.clip(157+noise*2.5,0,255).astype(np.uint8)
    Image.fromarray(rough).save(folder/'coat_rough.png')
    dx=(np.roll(noise,1,1)-np.roll(noise,-1,1))*.018
    dy=(np.roll(noise,-1,0)-np.roll(noise,1,0))*.018
    norm=np.stack((dx,dy,np.ones_like(noise)),axis=2)
    norm/=np.linalg.norm(norm,axis=2)[:,:,None]
    Image.fromarray(np.clip((norm*.5+.5)*255,0,255).astype(np.uint8)).save(folder/'coat_normal.png')
    im=Image.new('RGB',(1024,576),(218,221,207));d=ImageDraw.Draw(im)
    def font(size):return ImageFont.truetype('C:/Windows/Fonts/bahnschrift.ttf',size)
    d.rounded_rectangle((7,7,1016,568),radius=10,outline=(52,60,55),width=4)
    d.rectangle((30,30,994,129),fill=(41,56,50))
    d.text((51,43),'SPILLWAY / SERVICE',font=font(68),fill=(222,228,211))
    d.text((40,156),'SC-02',font=font(124),fill=(36,44,40))
    d.text((42,302),'CONTROL ENCLOSURE',font=font(48),fill=(47,55,50))
    d.line((43,370,976,370),fill=(75,83,76),width=3)
    d.text((42,397),'400 V    /    50 Hz    /    IP 55',font=font(42),fill=(43,51,46))
    d.text((42,471),'ISOLATE SUPPLY BEFORE OPENING',font=font(37),fill=(43,51,46))
    d.polygon([(833,160),(962,336),(705,336)],fill=(216,175,42),outline=(35,39,32),width=9)
    d.polygon([(842,191),(789,272),(836,268),(812,312),(891,239),(844,245)],fill=(30,35,30))
    im.save(folder/'label_color.png')
    tag=Image.new('RGB',(512,128),(25,31,28));td=ImageDraw.Draw(tag)
    td.text((256,64),'ISOLATOR',font=font(69),fill=(217,222,208),anchor='mm')
    tag.save(folder/'tag_color.png')
    mats={
      'body':((.39,.46,.43),.01,.96), 'door':((.45,.52,.48),.01,.94),
      'dark':((.10,.12,.115),.15,1.05), 'rubber':((.065,.075,.07),0,1.30),
      'alloy':((.63,.68,.65),.72,.63), 'red':((.47,.058,.035),.02,.78),
      'yellow':((.79,.58,.105),0,.98), 'green':((.09,.34,.17),.05,.48)}
    for name,(tint,metal,roughscale) in mats.items():
        text=f'''"Layer0"
{{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 g_flMetalness "{metal}"
 g_flRoughnessScaleFactor "{roughscale}"
 TextureColor "materials/spillway/service-cabinet-v1/coat_color.png"
 TextureNormal "materials/spillway/service-cabinet-v1/coat_normal.png"
 TextureRoughness "materials/spillway/service-cabinet-v1/coat_rough.png"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"
 g_flModelTintAmount "1"
}}
'''
        (folder/f'{name}.vmat').write_text(text)
    (folder/'label.vmat').write_text('''"Layer0"
{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 g_flMetalness "0.12"
 g_flRoughnessScaleFactor "0.72"
 TextureColor "materials/spillway/service-cabinet-v1/label_color.png"
 TextureNormal "materials/default/default_normal.tga"
 TextureRoughness "materials/default/default_rough.tga"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_vColorTint "[1 1 1 1]"
}
''')
    (folder/'tag.vmat').write_text((folder/'label.vmat').read_text().replace('label_color.png','tag_color.png'))
