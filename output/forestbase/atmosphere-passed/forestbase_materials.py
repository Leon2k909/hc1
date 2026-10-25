"""Forest Base's deterministic PBR palette; authored surfaces and foliage, no cloud dependencies.
Run with the project's Python runtime. World-scale tiles are in inches.
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.ndimage import gaussian_filter
import building_textures as BT
import map_kit as K

OUT = K.ASSETS / 'materials/forestbase'
RESOURCE = 'materials/forestbase'
TILES = dict(asphalt=192, asphalt_repair=143, asphalt_seam=128, concrete=128, plaster=128, steel=64, olive=64, roof=96,
             equipment_paint=96, dish_paint=128,
             vehicle_paint=96, vehicle_metal=80, vehicle_rubber=32, vehicle_canvas=96, vehicle_glass=32,
             vehicle_stencil_0=128, vehicle_stencil_1=128,
             timber=64, rubber=32, glass=32, yellow=32, lamp=32, screen=32,
             bark=48, needles=64, fence=64, tarp=64, mud=128, water=128, rock=256)
COLORS = dict(asphalt=(52,57,59), concrete=(134,135,126), plaster=(154,156,143),
              equipment_paint=(103,113,108), dish_paint=(153,158,150),
              steel=(52,59,58), olive=(78,86,57), roof=(100,111,111), timber=(110,94,65),
              rubber=(28,29,28), glass=(28,45,48), yellow=(172,142,46), lamp=(255,211,144),
              screen=(28,125,128), bark=(69,58,42), tarp=(63,72,42), mud=(67,57,42),
              water=(82,112,126), rock=(87,96,96), needles=(39,63,39), fence=(110,119,108))

def save(name, color, height, rough, metal=0, alpha=None, illum=0):
    OUT.mkdir(parents=True, exist_ok=True)
    color = np.clip(color,0,255).astype('uint8')
    Image.fromarray(color).save(OUT/f'{name}_color.png')
    size = color.shape[0]
    normals = BT.gl_normals(np.asarray(height)*np.ones((size,size)), 1.8)
    Image.fromarray(np.clip((normals*.5+.5)*255,0,255).astype('uint8')).save(OUT/f'{name}_normal.png')
    Image.fromarray(np.clip(np.asarray(rough)*np.ones((size,size))*255,0,255).astype('uint8')).save(OUT/f'{name}_rough.png')
    lines = ['// Tools/forestbase_materials.py', '"Layer0"', '{', ' shader "shaders/complex.shader"',
             ' F_SPECULAR "1"', f' g_flMetalness "{metal}"',
             f' TextureColor "{RESOURCE}/{name}_color.png"', f' TextureNormal "{RESOURCE}/{name}_normal.png"',
             f' TextureRoughness "{RESOURCE}/{name}_rough.png"',
             ' TextureAmbientOcclusion "materials/default/default_ao.tga"', ' g_flModelTintAmount "1"']
    if alpha is not None:
        Image.fromarray(np.asarray(alpha).astype('uint8')).save(OUT/f'{name}_alpha.png')
        lines += [' F_ALPHA_TEST "1"', ' F_RENDER_BACKFACES "1"', f' TextureTranslucency "{RESOURCE}/{name}_alpha.png"', ' g_flAlphaTestReference "0.35"']
    if illum:
        lines += [' F_SELF_ILLUM "1"', ' TextureSelfIllumMask "[1 1 1 0]"', ' g_flSelfIllumAlbedoFactor "1"', f' g_flSelfIllumBrightness "{illum}"']
    lines += ['}']
    K.write_text(OUT/f'{name}.vmat', '\n'.join(lines)+'\n')

def cargo_labels():
    """Authored weathered freight labels, independent of the tiled surface palette."""
    OUT.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(617)
    for index,title in enumerate(('COMMS EQUIPMENT','FIELD MAINTENANCE','SUPPLY / MEDICAL','FBXU 041732 6')):
        base=(188,182,151) if index<3 else (197,196,177)
        img=Image.new('RGB',(512,256),base); d=ImageDraw.Draw(img)
        bold=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',30)
        small=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',22)
        d.rectangle((12,12,499,243),outline=(44,48,39),width=4)
        d.text((25,26),title,fill=(29,34,27),font=bold)
        d.line((25,70,485,70),fill=(55,59,45),width=3)
        d.text((25,85),'FOREST BASE / LOGISTICS',fill=(35,40,31),font=small)
        d.text((25,115),'LOT 06-27    KEEP DRY',fill=(35,40,31),font=small)
        d.text((25,145),'20G1 / 24,000 KG' if index==3 else 'HANDLE WITH CARE',fill=(35,40,31),font=small)
        for x in range(28,354,5):
            if rng.random()>.22: d.rectangle((x,183,x+int(rng.integers(1,4)),223),fill=(31,36,28))
        # Scuffed ink and a few stains retain the label's useful large-scale contrast.
        for j in range(80):
            x,y=rng.integers(15,495),rng.integers(15,240)
            d.line((int(x),int(y),int(x+rng.integers(2,14)),int(y)),fill=base,width=1)
        img.save(OUT/f'cargo_{index}_color.png')
        K.write_text(OUT/f'cargo_{index}.vmat',f'''"Layer0"
{{
 shader "shaders/complex.shader"
 TextureColor "{RESOURCE}/cargo_{index}_color.png"
 TextureNormal "materials/default/default_normal.tga"
 TextureRoughness "[.74 .74 .74 0]"
}}
''')

def equipment_surfaces():
    """Fine satin powder coating for equipment housings and the satellite dish."""
    rng=np.random.default_rng(631); n=1024
    fine=rng.normal(size=(n,n)); stains=gaussian_filter(fine,24,mode='wrap')
    stains/=max(float(stains.std()),.0001)
    for name in ('equipment_paint','dish_paint'):
        color=np.asarray(COLORS[name])[None,None,:]*(1+.014*fine+.022*stains)[...,None]
        # Hairline scratches avoid masonry-sized grooves on small sheet-metal parts.
        scratch=np.zeros((n,n),dtype=np.float32)
        for _ in range(60):
            x,y=rng.integers(0,n,size=2); length=int(rng.integers(4,45))
            scratch[y,x:min(n,x+length)]=1
        color-=scratch[...,None]*10
        height=.5+fine*.0018-scratch*.003
        save(name,color,height,np.clip(.63+.025*stains+scratch*.06,.5,.76),metal=.04)
    print('Forest Base equipment coatings written.')

def ground_surfaces():
    """Reuse the authored/CC0 asphalt with a darker repair coat and fine sealant."""
    scanned=OUT/'scans/asphalt_02.vmat'
    source=(scanned if scanned.exists() else OUT/'asphalt.vmat').read_text()
    lines=[line for line in source.splitlines() if 'g_flTintColor' not in line]
    lines.insert(len(lines)-1,' g_flTintColor "[.46 .49 .50]"')
    K.write_text(OUT/'asphalt_repair.vmat','\n'.join(lines)+'\n')
    K.write_text(OUT/'asphalt_seam.vmat','''"Layer0"
{
 shader "shaders/complex.shader"
 TextureColor "[.018 .021 .022 1]"
 TextureNormal "materials/default/default_normal.tga"
 TextureRoughness "[.93 .93 .93 0]"
 TextureMetalness "[0 0 0 0]"
}
''')

def main():
    n = 1024
    rng = np.random.default_rng(8739)
    y,x = np.mgrid[:n,:n]
    fine = rng.standard_normal((n,n))
    large = gaussian_filter(fine,22,mode='wrap'); large /= large.std()
    mid = gaussian_filter(fine,3,mode='wrap'); mid /= mid.std()
    for name in ('asphalt','concrete','plaster','steel','olive','roof','timber','rubber','glass','yellow','lamp','screen','bark','tarp','mud'):
        color = np.array(COLORS[name])[None,None,:] * (1+.065*large+.045*fine)[...,None]
        height = .5 + .018*mid + .007*fine
        rough = .7 + .04*mid
        metal = 0
        if name == 'asphalt':
            wet = np.clip((large+.6)/2,0,1)
            cracks = np.exp(-np.abs(np.sin(x*.017 + np.sin(y*.012)*1.4))*80) * (large>.2)
            color *= (1-.21*wet-.3*cracks)[...,None]
            rough = .77-.57*wet; height -= .07*cracks
        elif name in ('steel','olive','roof'):
            scratches = np.maximum(fine-2,0)*np.exp(-((y%31)/3)**2)
            color += scratches[...,None]*35
            rust = np.clip((large-2.2)*.17,0,.12)
            color = color*(1-rust[...,None])+np.array((108,65,34))*rust[...,None]
            rough = .39 + .16*rust+.02*fine; metal = .72 if name != 'olive' else .08
            if name=='olive':
                # Paint varies at the grain scale; broad clouds read as camouflage noise.
                color=np.array(COLORS[name])[None,None,:]*(1+.008*large+.015*fine)[...,None]
                color+=scratches[...,None]*12
                height=.5+.0015*mid+.001*fine
                rough=.57+.015*mid
            if name=='roof':
                rib = .5+.5*np.cos(x*np.pi/32)
                height += rib*.28; color *= (.78+.22*rib)[...,None]
        elif name == 'concrete':
            seam = (x%512<3)|(y%512<3)
            pores = fine < -2.3
            height -= seam*.2+pores*.08; color *= (1-.15*seam-.25*pores)[...,None]
        elif name in ('bark','timber'):
            grain = np.sin(x*.18+mid*.6)+np.sin(x*.41+large)
            height += .09*grain; color *= (1+.16*grain)[...,None]
        elif name == 'rubber':
            tread = ((x+y//48*20)%70<12)
            height -= tread*.18; color *= (1-.25*tread)[...,None]; rough = .9
        elif name == 'glass':
            rough = .11; height *= 0
        elif name == 'lamp':
            rough = .25; height *= 0
        elif name == 'screen':
            grid = (x%96<2)|(y%96<2)
            color *= (.4+.4*grid)[...,None]
            color[(np.sin(x*.012)*80+500-y)**2<9] = (95,222,160)
            rough = .18
        elif name == 'tarp':
            weave = .5*np.sin(x*np.pi/2)+.5*np.cos(y*np.pi/2)
            color=np.array(COLORS[name])[None,None,:]*(1+.016*large+.015*fine)[...,None]
            height=.5+weave*.006+.003*mid; rough = .83
        elif name == 'mud':
            color *= (1+.15*mid)[...,None]; height += mid*.07; rough=.55+.12*large
        save(name,color,height,np.clip(rough,.06,.97),metal,illum=2.5 if name=='lamp' else .6 if name=='screen' else 0)
    # Alpha-tested chain link: fine wire diamonds, not opaque fence panels.
    alpha = np.zeros((n,n),dtype='uint8')
    diag = np.minimum((x+y)%256,256-(x+y)%256)
    other = np.minimum((x-y)%256,256-(x-y)%256)
    alpha[(diag<7)|(other<7)]=255
    save('fence', np.tile(COLORS['fence'],(n,n,1)),0,.48,.8,alpha)
    # A real twig silhouette, with hundreds of distinct needles and a transparent perimeter.
    leaf = Image.new('RGB',(n,n),COLORS['needles']); mask = Image.new('L',(n,n),0)
    draw,md = ImageDraw.Draw(leaf),ImageDraw.Draw(mask)
    for side in (-1,1):
        for k in range(38):
            by = 870-k*18; reach = (1-k/43)*380
            ex,ey = 512+side*reach,by-150
            draw.line((512,by,ex,ey),fill=(64,77,43),width=7); md.line((512,by,ex,ey),fill=255,width=7)
            for f in np.linspace(.08,1,24):
                px,py = 512+(ex-512)*f,by+(ey-by)*f
                for tilt in (-1,1):
                    tip = (px+side*rng.uniform(20,38),py+tilt*rng.uniform(15,30)-20)
                    c = tuple(int(v) for v in np.array((43,69,38))*rng.uniform(.7,1.4))
                    draw.line((px,py,*tip), fill=c,width=3); md.line((px,py,*tip),fill=255,width=3)
    draw.line((512,940,512,140),fill=(80,66,44),width=10); md.line((512,940,512,140),fill=255,width=10)
    save('needles',np.array(leaf),0,.86,alpha=np.array(mask))
    # Use the existing terrain scan at a plausible world scale, preserving all PBR maps.
    rock='"Layer0"\n{\n shader "shaders/complex.shader"\n F_SPECULAR "1"\n'
    for prop,suffix in [('Color','color'),('Normal','normal'),('Roughness','rough'),('AmbientOcclusion','ao')]:
        rock += f' Texture{prop} "materials/terrain/rock_{suffix}.png"\n'
    K.write_text(OUT/'rock.vmat',rock+'}\n')
    K.write_text(OUT/'water.vmat','"Layer0"\n{\n shader "shaders/forestbase_water.shader"\n}\n')
    # Legible signs: a single atlas per area, mapped once across each panel.
    for letter,label in [('A','MOTOR POOL'),('B','BARRACKS'),('C','COMMAND'),('D','LOGISTICS'),('E','MAINTENANCE'),('F','CATWALK')]:
        img=Image.new('RGB',(1024,256),(38,45,38)); d=ImageDraw.Draw(img)
        fontpath='C:/Windows/Fonts/arialbd.ttf'
        d.rectangle((10,10,1013,245),outline=(170,164,119),width=6)
        d.text((38,22),letter,fill=(228,202,112),font=ImageFont.truetype(fontpath,158))
        d.text((205,57),label,fill=(208,212,190),font=ImageFont.truetype(fontpath,65))
        img.save(OUT/f'sign_{letter}_color.png')
        K.write_text(OUT/f'sign_{letter}.vmat',f'"Layer0"\n{{\n shader "shaders/complex.shader"\n TextureColor "{RESOURCE}/sign_{letter}_color.png"\n TextureNormal "materials/default/default_normal.tga"\n TextureRoughness "[.65 .65 .65 0]"\n}}\n')
    cargo_labels()
    equipment_surfaces()
    ground_surfaces()
    import forestbase_vehicle_materials
    forestbase_vehicle_materials.main()
    import forestbase_water
    forestbase_water.main()
    print('Forest Base PBR palette, equipment coatings, foliage, chain link, signs and cargo labels written.')

if __name__=='__main__':
    import sys
    cargo_labels() if '--labels' in sys.argv else equipment_surfaces() if '--sheets' in sys.argv else main()
