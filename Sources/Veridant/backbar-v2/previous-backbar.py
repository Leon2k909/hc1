"""Walnut back-bar cabinetry with recognisable labelled glass bottles."""
import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter
import map_kit as K
import riverdale_parts as P

PREFIX='materials/veridant/backbar-v1'
NAMES=('walnut','trim','metal','glass_green','glass_amber','glass_clear',
       'liquid_red','liquid_amber','foil_dark','foil_gold','labels')
MATERIALS={f'vr_backbar_{name}':f'{PREFIX}/{name}.vmat' for name in NAMES}
X=np.array((1.,0.,0.));Y=np.array((0.,1.,0.));Z=np.array((0.,0.,1.))


def lathe(model,centre,profile,paint,sides=20,caps=True):
    centre=np.array(centre);rings=[];normals=[]
    for j,(height,radius) in enumerate(profile):
        previous=profile[max(0,j-1)];following=profile[min(len(profile)-1,j+1)]
        slope=(following[1]-previous[1])/max(following[0]-previous[0],1e-6)
        ns=[P.unit((math.cos(a),math.sin(a),-slope)) for a in np.linspace(0,math.tau,sides,endpoint=False)]
        rings.append([centre+np.array((radius*math.cos(a),radius*math.sin(a),height))
                      for a in np.linspace(0,math.tau,sides,endpoint=False)])
        normals.append(ns)
    for j in range(len(rings)-1):
        for i in range(sides):
            k=(i+1)%sides
            # Tangent around a ring, then upward: outward winding.
            model.polygon(paint,(rings[j][i],rings[j][k],rings[j+1][k],rings[j+1][i]),
                          normals=(normals[j][i],normals[j][k],normals[j+1][k],normals[j+1][i]))
    if caps:
        P.card(model,paint,rings[0],-Z);P.card(model,paint,rings[-1],Z)


def bottle(model,u,d,z,rng,kind,label):
    spirit=kind!=0
    height=rng.uniform(9.0,10.8) if spirit else rng.uniform(10.9,12.2)
    radius=rng.uniform(1.18,1.43) if spirit else rng.uniform(1.12,1.32)
    shoulder=.61 if spirit else .65
    profile=[(0.,radius*.87),(.12,radius*.98),(.32,radius),
             (height*shoulder,radius*.99),(height*(shoulder+.06),radius*.91),
             (height*(shoulder+.12),radius*.61),(height*(shoulder+.18),radius*.35),
             (height-.52,radius*.34),(height-.39,radius*.40),(height-.27,radius*.40)]
    body=('glass_green','glass_amber','glass_clear')[kind]
    lathe(model,(u,d,z),profile,'vr_backbar_'+body)
    if kind!=2:
        fill=height*rng.uniform(.54,.61);r=radius-.13
        lathe(model,(u,d,z),[(.16,r*.90),(.36,r),(fill-.06,r),(fill,r*.99)],
              'vr_backbar_liquid_red' if kind==0 else 'vr_backbar_liquid_amber',sides=16)
    neck=radius*.40+.035
    foil='vr_backbar_foil_dark' if kind==0 or rng.random()<.5 else 'vr_backbar_foil_gold'
    lathe(model,(u,d,z),[(height-.80,neck*.95),(height-.75,neck),(height-.10,neck),
                        (height-.03,neck*.95)],foil,sides=16)
    lathe(model,(u,d,z),[(height-.72,neck*1.01),(height-.65,neck*1.01)],'vr_backbar_metal',sides=16)
    yaw=rng.uniform(-.15,.15)
    low=height*.19;high=height*.49
    a0,a1=math.radians(27)+yaw,math.radians(153)+yaw
    col,row=label%4,label//4
    for a,b in zip(np.linspace(a0,a1,13)[:-1],np.linspace(a0,a1,13)[1:]):
        ta,tb=(a-a0)/(a1-a0),(b-a0)/(a1-a0)
        rr=radius+.014
        points=[np.array((u+rr*math.cos(t),d+rr*math.sin(t),z+h))
                for t,h in ((a,low),(b,low),(b,high),(a,high))]
        # OBJ V is inverted on import; image top maps to higher source V.
        uv=[((col+.92-.84*t)/4,1-(row+yy)/2) for t,yy in ((ta,.90),(tb,.90),(tb,.10),(ta,.10))]
        P.card(model,'vr_backbar_labels',points,(math.cos((a+b)/2),math.sin((a+b)/2),0),uv=uv)
    return height


def build_into(model,lo,hi,z0,face='+e'):
    e0,n0=lo;e1,n1=hi
    out=np.array({'+e':(1.,0.,0.),'-e':(-1.,0.,0.),'+n':(0.,1.,0.),'-n':(0.,-1.,0.)}[face])
    right=np.cross(Z,out)
    width=n1-n0 if face.endswith('e') else e1-e0
    depth=e1-e0 if face.endswith('e') else n1-n0
    front=np.array(((e1 if face=='+e' else e0) if face.endswith('e') else (e0+e1)/2,
                    (n1 if face=='+n' else n0) if face.endswith('n') else (n0+n1)/2,z0))
    axes=np.array((right,out,Z));local=K.Model();rng=np.random.default_rng(int(abs(e0*7+n0*3))%1000)
    count=0

    def wood(centre,size,bevel=.12):
        mat='vr_backbar_walnut';start=len(local.polygons[mat])
        P.bevel_box(local,np.array(centre),(X,Y,Z),size,mat,bevel=bevel)
        for index in range(start,len(local.polygons[mat])):
            points,normal=local.polygons[mat][index]
            along=P.unit(max((points[(j+1)%len(points)]-p for j,p in enumerate(points)),key=np.linalg.norm))
            across=np.cross(normal,along)
            local.polygon_uvs[(mat,index)]=[(float(np.dot(p,across)/10+.21),float(np.dot(p,along)/48+.17)) for p in points]

    # A thin backing, separate stiles, actual shelves and closed base storage.
    wood((0,-depth+.45,45),(width,.90,90),.12)
    for side in (-1,1):wood((side*(width/2-1),-depth/2,45),(2.,depth,90),.18)
    wood((0,-depth/2,89.25),(width,depth,1.5),.16)
    wood((0,-depth/2,2),(width,depth,4),.15)
    wood((0,-depth/2,39.40),(width,depth,1.20),.17)
    bays=max(1,round(width/34));bay_width=(width-4)/bays
    for divider in range(1,bays):
        u=-width/2+2+divider*bay_width
        wood((u,-depth/2,64.5),(1.15,depth,49),.12)
    for bay in range(bays):
        centre=-width/2+2+(bay+.5)*bay_width
        door_width=bay_width-1.0
        # Recessed centre panel with eased rails/stiles.
        wood((centre,-.30,21),(door_width-2,.64,31),.10)
        for side in (-1,1):wood((centre+side*(door_width/2-.50),-.05,21),(1.,.9,33),.11)
        for height in (5.,37.):wood((centre,-.05,height),(door_width,.9,1.1),.10)
        for u in (centre-2,centre+2):
            P.rod(local,(u,.4,33.1),(u,.95,33.1),.12,'vr_backbar_metal',8,caps=True)
        P.rod(local,(centre-2.1,.95,33.1),(centre+2.1,.95,33.1),.16,'vr_backbar_metal',10,caps=True)
        for level,height in enumerate((40.,58.,76.)):
            if level:
                wood((centre,-depth/2,height-.6),(bay_width-.2,depth,1.2),.16)
            # A narrow warm diffuser is integrated into the shelf edge.
            P.card(local,'vr_led_soft',[(centre-bay_width/2+.7,.025,height-.61),
                   (centre+bay_width/2-.7,.025,height-.61),(centre+bay_width/2-.7,.025,height-.46),
                   (centre-bay_width/2+.7,.025,height-.46)],Y)
            amount=max(2,int((bay_width-7)/4.7))-(1 if level==2 else 0)
            span=min(bay_width-8,amount*4.4)
            for index,u in enumerate(np.linspace(centre-span/2,centre+span/2,max(1,amount))):
                u+=rng.uniform(-.28,.28);d=-rng.uniform(3.2,min(5.2,depth-2))
                kind=(index+bay+level)%3;label=(index+bay*2+level*3)%8
                bottle(local,u,d,height+.025,rng,kind,label);count+=1
    model.material_overrides.update(MATERIALS)
    model.material_overrides['vr_led_soft']='materials/veridant/vr_led_soft.vmat'
    model.tile_overrides.update({p:12. for p in MATERIALS})
    model.tile_overrides['vr_led_soft']=12.
    # right/out/up is reflected relative to plan coordinates; card() rewinds it.
    for paint,rows in local.polygons.items():
        for index,(points,normal) in enumerate(rows):
            ns=local.polygon_normals.get((paint,index))
            P.card(model,paint,[front+p@axes for p in points],normal@axes,
                   normals=[n@axes for n in ns] if ns is not None else None,
                   uv=local.polygon_uvs.get((paint,index)))
    return {'bottles':count,'bays':bays,'width':width,'depth':depth}


def write_materials(directory):
    out=Path(directory);out.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(814503);n=1024
    def noise(sigma):
        a=gaussian_filter(rng.normal(size=(n,n)),sigma,mode='wrap');return a/max(a.std(),1e-8)
    long=noise((58,3));fine=noise((18,.8));wide=noise(35)
    colour=(1+.075*long+.025*fine+.025*wide)[...,None]*np.array((88.,57.,35.))
    Image.fromarray(np.clip(colour,0,255).astype('uint8')).save(out/'walnut_color.png')
    h=.004*long+.0015*fine;dx=(np.roll(h,-1,1)-np.roll(h,1,1))/(20/n);dy=(np.roll(h,-1,0)-np.roll(h,1,0))/(96/n)
    normal=np.stack((-dx,dy,np.ones_like(dx)),axis=-1);normal/=np.linalg.norm(normal,axis=-1)[...,None]
    Image.fromarray(np.clip((normal*.5+.5)*255,0,255).astype('uint8')).save(out/'walnut_normal.png')
    Image.fromarray(np.clip((.68+.04*long+.025*fine)*255,0,255).astype('uint8')).save(out/'walnut_rough.png')
    Image.new('RGB',(16,16),(128,128,255)).save(out/'flat_normal.png')
    atlas=Image.new('RGB',(2048,1024));draw=ImageDraw.Draw(atlas)
    serif=ImageFont.truetype('C:/Windows/Fonts/georgiab.ttf',60)
    small=ImageFont.truetype('C:/Windows/Fonts/georgia.ttf',27)
    titles=('ALTO','COSTA','BOTANIC','AMBRE','VERDE','SALVO','RIVA','NO. 8')
    palettes=(((218,207,173),(73,31,35)),((226,219,197),(42,61,75)),((202,213,192),(36,58,43)),
              ((200,166,100),(58,37,24)),((222,215,190),(44,67,38)),((57,47,39),(204,177,120)),
              ((226,220,201),(66,78,83)),((205,197,171),(58,52,43)))
    for i,title in enumerate(titles):
        x=(i%4)*512;y=(i//4)*512;paper,ink=palettes[i]
        draw.rectangle((x,y,x+511,y+511),fill=paper)
        draw.rectangle((x+35,y+38,x+477,y+474),outline=ink,width=4)
        draw.line((x+65,y+113,x+447,y+113),fill=ink,width=2)
        draw.text((x+256,y+173),title,font=serif,fill=ink,anchor='mm')
        draw.text((x+256,y+247),'RESERVA' if i%3==0 else 'SMALL BATCH',font=small,fill=ink,anchor='mm')
        draw.ellipse((x+211,y+302,x+301,y+392),outline=ink,width=3)
        draw.text((x+256,y+347),str(12+i),font=small,fill=ink,anchor='mm')
        draw.text((x+256,y+438),'750 ml   /   EST. 1924',font=small,fill=ink,anchor='mm')
    atlas.save(out/'labels_color.png')
    colours={'trim':(.065,.060,.050),'metal':(.43,.32,.18),'liquid_red':(.15,.028,.024),
             'liquid_amber':(.39,.17,.045),'foil_dark':(.065,.050,.041),'foil_gold':(.50,.35,.14)}
    for name in NAMES:
        if name.startswith('glass_'):
            tint={'glass_green':(.40,.63,.29),'glass_amber':(.68,.40,.15),'glass_clear':(.93,.96,.94)}[name]
            text=('// Tools/veridant_backbar.py\n"Layer0"\n{\n    shader "shaders/glass.shader"\n'
                  '    F_GLASS_QUALITY "2"\n    g_bFogEnabled "1"\n    g_flBlurAmount "0.0"\n'
                  '    g_flRefractionStrength "1.008"\n    AlbedoAbsorption "0.28"\n'
                  '    g_flTintColor "[1 1 1 0]"\n'
                  f'    TextureColor "[{tint[0]} {tint[1]} {tint[2]} 0]"\n'
                  '    TextureNormal "materials/default/default_normal.tga"\n'
                  '    TextureRoughness "[0.10 0.10 0.10 0]"\n    TextureMetalness "[0 0 0 0]"\n'
                  '    TextureAmbientOcclusion "[1 1 1 0]"\n    TextureBlendMask "materials/default/default_blend.tga"\n'
                  '    TextureTintMask "materials/default/default.tga"\n    TextureTranslucency "materials/default/default_trans.tga"\n}\n')
        else:
            colour=f'{PREFIX}/walnut_color.png' if name=='walnut' else f'{PREFIX}/labels_color.png' if name=='labels' else 'materials/default/default_color.tga'
            normal=f'{PREFIX}/walnut_normal.png' if name=='walnut' else f'{PREFIX}/flat_normal.png'
            rough=f'{PREFIX}/walnut_rough.png' if name=='walnut' else '[0.65 0.65 0.65 0]' if name in ('trim','labels') else '[0.23 0.23 0.23 0]'
            tint=colours.get(name,(1,1,1));metal=.85 if name=='metal' else .55 if name=='foil_gold' else 0
            text=('// Tools/veridant_backbar.py\n"Layer0"\n{\n    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n'
                  f'    g_flMetalness "{metal}"\n    g_flRoughnessScaleFactor "1"\n'
                  f'    TextureColor "{colour}"\n    TextureNormal "{normal}"\n    TextureRoughness "{rough}"\n'
                  '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n'
                  f'    g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"\n    g_flModelTintAmount "1.0"\n}}\n')
        (out/f'{name}.vmat').write_text(text)
