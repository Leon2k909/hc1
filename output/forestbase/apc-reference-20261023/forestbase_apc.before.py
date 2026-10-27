"""Reference FB/041 APC finish. Visual-only detail over the existing parked vehicle.

Authored chassis/wheel collision proxies and the placement are retained verbatim.
No additional scene objects, lights, gameplay components or per-frame work.
"""
import math
from collections import defaultdict
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
import map_kit as K

RESOURCE='materials/forestbase/apc'
PAINTS=('apc_armor','apc_metal','apc_rubber','apc_stencil','apc_amber','apc_red')

def configure(m):
    for p in PAINTS:
        m.material_overrides[p]=f'{RESOURCE}/{p[4:]}.vmat'
        m.tile_overrides[p]=160 if p=='apc_armor' else 36

def refine(m,api):
    configure(m)
    if isinstance(m,api['CollisionOnlyModel']):return
    out=K.Model();configure(out)
    for paint,faces in m.polygons.items():
        for i,(pts,norm) in enumerate(faces):
            a=np.asarray(pts);z0,z1=a[:,2].min(),a[:,2].max()
            # Replace the old cylinder turret, short pipe gun and curved fenders.
            turret=z0>=100.99 and z1>=106.99 and a[:,0].min()>-70 and a[:,0].max()<75 and np.abs(a[:,1]).max()<32
            hatch=z0>=100.99 and z1<106.5 and a[:,0].min()>=11 and a[:,0].max()<=74 and a[:,1].min()>=-29 and a[:,1].max()<=-3
            fender=paint=='vehicle_paint' and z0>=22.9 and z1<=50.1 and np.abs(a[:,1]).max()>66.9
            if turret or hatch or fender or paint=='vehicle_stencil_1':continue
            target={'vehicle_paint':'apc_armor','vehicle_metal':'apc_metal','vehicle_rubber':'apc_rubber'}.get(paint,paint)
            out.polygon(target,pts,normal=norm,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))
    box=api['box'];bevel=api['bevel_box'];tube=api['tube']
    def b(a,c,p='apc_armor',r=.4):bevel(out,a,c,p,r)
    def rod(a,c,r=.5,p='apc_metal',segments=8):tube(out,a,c,r,p,segments=segments)
    def face(pts,p='apc_armor',normal=None):
        pts=[np.asarray(q,float) for q in pts]
        if normal is not None and np.dot(np.cross(pts[1]-pts[0],pts[2]-pts[0]),normal)<0:pts.reverse()
        out.polygon(p,pts)
    def bolt(c,axis=(0,0,1),r=.65):
        c=np.asarray(c,float);axis=K.normalise(axis)
        rod(c,c+axis*.4,r,'apc_metal',6)
    def handle(a,c,up=(0,0,2),r=.45):
        a=np.asarray(a,float);c=np.asarray(c,float);up=np.asarray(up,float)
        rod(a,a+up,r);rod(a+up,c+up,r);rod(c+up,c,r)
    # Low, faceted turret, separate armor cheek plates and a barrel with a
    # real open muzzle. Silhouette and proportions follow the reference.
    rings=[]
    for z,rx,ry in ((107,25,23),(111,25,23),(128,21,20)):
        rings.append([(-20+rx*math.cos(a),ry*math.sin(a),z) for a in np.linspace(0,math.tau,16,endpoint=False)])
    api['loft'](out,rings,'apc_armor')
    rod((-20,0,101),(-20,0,107),26,'apc_metal',40)
    for side in (-1,1):
        b((-32,min(side*20,side*24),113),(-13,max(side*20,side*24),125),'apc_armor',.7)
        for x in (-36,-21,-7):bolt((x,side*22.3,111),(0,side,.1),.5)
    b((0,-5,117.8),(14,5,127.5),'apc_metal',1)
    rod((9,0,123),(23,0,123),4,'apc_metal',24)
    for x in (12,19,24,79):rod((x,0,123),(x+1.1,0,123),3.1 if x<25 else 2.15,'apc_metal',24)
    rod((21,0,123),(89,0,123),1.65,'apc_metal',20)
    # Hollow muzzle brake: no capped pipe end or painted-on bore.
    for x0,x1 in ((88,90),(97,99)):
        outer=[(-3.5,-3.1),(3.5,-3.1),(3.5,3.1),(-3.5,3.1)]
        inner=[(-1.8,-1.5),(1.8,-1.5),(1.8,1.5),(-1.8,1.5)]
        for k in range(4):
            j=(k+1)%4
            face([(x1,*((y,123+z))) for y,z in (outer[k],outer[j],inner[j],inner[k])],'apc_metal',(-1,0,0) if x1==90 else (1,0,0))
            face([(x0,outer[k][0],123+outer[k][1]),(x1,outer[k][0],123+outer[k][1]),(x1,outer[j][0],123+outer[j][1]),(x0,outer[j][0],123+outer[j][1])],'apc_metal')
    for yy in (-3.1,3.1):
        for zz in (120.5,125.5):b((89,yy-.35,zz-.4),(98,yy+.35,zz+.4),'apc_metal',.1)
    rod((-25,0,128),(-25,0,130),11,'apc_armor',32)
    handle((-29,-2,130),(-21,-2,130),up=(0,0,2.1))
    # Stabilized commander's sight, lenses, rails and a turret whip antenna.
    b((-35,-12,130),(-24,1,141),'apc_armor',.8)
    b((-38,-13,140),(-19,2,146),'apc_metal',.55)
    for yy in (-9,-3):
        rod((-18.9,yy,143),(-18.5,yy,143),1.45,'vehicle_glass',16)
    for xx in (-36,-22):
        for yy in (-11,0):bolt((xx,yy,146),r=.4)
    for yy in (-15,5):handle((-39,yy,138),(-20,yy,138),up=(0,0,9),r=.35)
    rod((-36,15,126),(-36,15,132),1.3,'apc_metal',12)
    rod((-36,15,132),(-36,15,174),.25,'apc_metal',8)
    # Shoulder tread blocks and angular armored wheel surrounds.
    for x in (-104,-37,33,106):
        for side in (-1,1):
            for k in range(28):
                a=math.tau*k/28
                for row in (-1,1):
                    tangent=np.array((-math.sin(a),0,math.cos(a)))
                    radial=np.array((math.cos(a),0,math.sin(a)))
                    c=(x+22.4*math.cos(a),side*58+row*6.5,23+22.4*math.sin(a))
                    out.oriented_box(c,(tangent,(0,-1,0),radial),(3.1,3.1,1.3),'apc_rubber')
            outer=[(-30,3),(-30,14),(-18,29),(18,29),(30,14),(30,3)]
            inner=[(-26,4),(-26,12),(-16,25),(16,25),(26,12),(26,4)]
            for k in range(5):
                q=[(x+xx,side*67.4,23+zz) for xx,zz in (outer[k],outer[k+1],inner[k+1],inner[k])]
                face(q,normal=(0,side,0))
                q=[(x+xx,yy,23+zz) for (xx,zz),yy in ((outer[k],side*51),(outer[k+1],side*51),(outer[k+1],side*67.4),(outer[k],side*67.4))]
                face(q,normal=(0,0,1))
            for xx,zz in (outer[1],outer[2],outer[3],outer[4]):bolt((x+xx,side*67.6,23+zz),(0,side,0),.48)
    def sidepoint(x,z,side,offset=0):
        if z<=79:y=54-max(0,z-60)*8/19
        else:
            t=(z-79)/22;y=47-7*t;edge=88-6*t;tip=115-9*t
            if x>edge:y-=(x-edge)*(17-3*t)/(tip-edge)
        return np.array((x,side*(y+offset),z))
    # Weld lines, captive fasteners, panel latches and actual louver blades.
    for side in (-1,1):
        for zz in (61,78):
            for xx in range(-132,88,16):bolt(sidepoint(xx,zz,side,.3),(0,side,.42),.57)
        for xx in (-111,-57,-8,30,78):
            for zz in (84,97):bolt(sidepoint(xx,zz,side,.4),(0,side,.32),.55)
        for left,right in ((-55,-11),(32,75)):
            for xx in (left+5,right-5):
                a=sidepoint(xx,85,side,.9);c=sidepoint(xx,90,side,.9)
                rod(a,c,.75);rod(a+np.array((0,side*.4,1)),c+np.array((0,side*.4,-1)),.45,'apc_armor')
            handle(sidepoint((left+right)/2-3,91,side,1),sidepoint((left+right)/2+3,91,side,1),up=(0,side*1.2,0),r=.4)
        for left,right,low,high in ((-113,-76,83,99),(84,103,84,96)):
            q=[sidepoint(left,low,side,.65),sidepoint(right,low,side,.65),sidepoint(right,high,side,.65),sidepoint(left,high,side,.65)]
            face(q,'apc_metal',(0,side,0))
            for zz in np.arange(low+1,high,1.8):
                a=sidepoint(left+1,zz,side,1.3);c=sidepoint(right-1,zz,side,1.3)
                out.beam(a,c,(.9,.75),'apc_metal')
            for xx in (left-.5,right+.5):rod(sidepoint(xx,low,side,1),sidepoint(xx,high,side,1),.55,'apc_armor')
            for zz in (low-.5,high+.5):rod(sidepoint(left,zz,side,1),sidepoint(right,zz,side,1),.55,'apc_armor')
        # Two secured pioneer tools; handle, shaft, pressed blade and brackets.
        for zz in (68,73):rod(sidepoint(29,zz,side,2),sidepoint(94,zz,side,2),.7,'timber',10)
        blade=[sidepoint(x,zz,side,2.3) for x,zz in ((92,64),(106,64),(110,68),(110,75),(106,78),(92,77))]
        face(blade,'apc_metal',(0,side,0))
        rod(sidepoint(93,71,side,2.7),sidepoint(105,71,side,2.7),.45,'apc_metal')
        for xx in (32,86):
            for zz in (67,74):
                rod(sidepoint(xx-2,zz,side,3),sidepoint(xx+2,zz,side,3),.75)
                bolt(sidepoint(xx,zz,side,3.5),(0,side,0),.5)
        handle(sidepoint(23,70.5,side,2),sidepoint(29,70.5,side,2),up=(0,0,3),r=.6)
        # Stowed can and a strapped canvas field pouch near the bow.
        ya,yb=sorted((side*42,side*51))
        b((119,ya,61),(134,yb,84),'apc_armor',1.2)
        for zz in (66,79):rod((120,side*51.4,zz),(133,side*51.4,zz),.65,'vehicle_canvas')
        for a,c in (((121,side*51.6,65),(132,side*51.6,79)),((121,side*51.6,79),(132,side*51.6,65))):rod(a,c,.45,'apc_armor')
        handle((122,side*46,84),(130,side*46,84),up=(0,0,3),r=.65)
        rod((131,side*45,84),(131,side*45,85.2),2,'apc_metal',12)
        ya,yb=sorted((side*47,side*56))
        b((106,ya,75),(117,yb,90),'vehicle_canvas',1.1)
        rod((111.5,side*56.2,75),(111.5,side*56.2,90),.8,'timber',8)
        # Rear markers and their armored housings stay within the old footprint.
        b((-147,min(side*34,side*43),45),(-143,max(side*34,side*43),60),'apc_metal',.65)
        b((-147.4,min(side*36,side*41),47),(-147.1,max(side*36,side*41),53),'apc_red',.15)
        b((-147.4,min(side*36,side*41),54),(-147.1,max(side*36,side*41),58),'apc_amber',.15)
        for xx in (-64,87):
            p=sidepoint(xx,42,side,.6);rod(p,p+np.array((0,side*.4,0)),1.6,'apc_amber',12)
        # New crisp, weathered unit stencil and chevrons follow the armor plane.
        pts=[sidepoint(-58,64,side,.32),sidepoint(21,64,side,.32),sidepoint(21,76,side,.32),sidepoint(-58,76,side,.32)]
        coords=[(0,0),(1,0),(1,1),(0,1)]
        if side>0:pts.reverse();coords.reverse()
        out.polygon('apc_stencil',pts,uv=coords)
    # Rear roof stowage rack, cans, straps and six tie-down handles.
    for xx in (-130,-115,-100,-85):
        for yy in (-17,5):
            b((xx,yy,103),(xx+12,yy+17,114),'apc_armor',.6)
            rod((xx+6,yy,114.4),(xx+6,yy+17,114.4),.45,'apc_metal')
    for xx in (-134,-70):
        for yy in (-36,30):rod((xx,yy,102),(xx,yy,117),.65)
        rod((xx,-36,117),(xx,30,117),.7)
    for yy in (-36,30):
        for zz in (108,117):rod((-134,yy,zz),(-70,yy,zz),.7)
    for xx in (24,61,92):
        for yy in (-17,17):
            if xx!=92:rod((xx,yy,101),(xx,yy,102.4),10,'apc_armor',24)
            handle((xx-4,yy,103),(xx+4,yy,103),up=(0,0,2),r=.45)
            for ax in (-8,8):bolt((xx+ax,yy,102.6),r=.45)
    # Consistent local UVs stop the coating changing when the map chunk is rebuilt.
    for paint,faces in out.polygons.items():
        for i,(pts,norm) in enumerate(faces):
            if paint=='apc_stencil':continue
            if paint in PAINTS:
                axis=int(np.argmax(np.abs(norm)));scale=160 if paint=='apc_armor' else 36
                axes=(0,2) if axis==1 else (1,2) if axis==0 else (0,1)
                out.polygon_uvs[(paint,i)]=[(q[axes[0]]/scale+.25,q[axes[1]]/scale+.37) for q in pts]
    m.polygons=out.polygons;m.polygon_uvs=out.polygon_uvs;m.polygon_normals=out.polygon_normals
    configure(m)

def materials(out,source):
    """Generated albedo plus restrained PBR maps and deterministic stencils."""
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    image=Image.open(source).convert('RGB').resize((2048,2048),Image.Resampling.LANCZOS)
    image.save(out/'armor_color.png',compress_level=3)
    # Restrained paint grain; broad camouflage color regions never become bumps.
    gray=np.asarray(image.convert('L'),float)
    smooth=np.asarray(image.convert('L').filter(ImageFilter.GaussianBlur(2)),float)
    dy,dx=np.gradient(gray-smooth)
    normal=np.empty((*gray.shape,3),dtype='uint8')
    normal[:,:,0]=np.clip(128-dx*.35,112,144);normal[:,:,1]=np.clip(128+dy*.35,112,144);normal[:,:,2]=255
    Image.fromarray(normal).save(out/'armor_normal.png',compress_level=3)
    # Baked lighting and shader-level grime are deliberately avoided here.
    specs=[('armor',None,.71,.05),('metal',(46,49,42),.57,.28),('rubber',(31,30,25),.79,0),('amber',(177,92,15),.48,.05),('red',(133,24,16),.5,.03)]
    rng=np.random.default_rng(8841)
    for name,color,rough,metal in specs:
        if color is not None:
            n=512;a=np.clip(np.array(color)[None,None,:]+rng.normal(0,1,(n,n,1)),0,255).astype('uint8')
            im=Image.fromarray(a);d=ImageDraw.Draw(im)
            if name=='metal':
                for k in range(260):
                    x,y=rng.integers(0,n,2);d.line((int(x),int(y),int(min(x+rng.integers(1,12),511)),int(y)),fill=(77,80,72),width=1)
            if name=='rubber':
                dust=Image.fromarray(rng.integers(0,255,(32,32),dtype=np.uint8)).resize((n,n),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(8))
                a=np.asarray(im).astype(float);mask=np.clip((np.asarray(dust,float)-115)/140,0,.3)
                a=a*(1-mask[:,:,None])+np.array((85,67,44))*mask[:,:,None];im=Image.fromarray(a.astype('uint8'))
            im.save(out/(name+'_color.png'),compress_level=3)
            Image.new('RGB',(n,n),(128,128,255)).save(out/(name+'_normal.png'))
        Image.new('RGB',(512,512),(int(rough*255),)*3).save(out/(name+'_rough.png'))
        tint=' CoatingTint "[.60 .66 .53]"\n CoatingDesaturation ".08"\n' if name=='armor' else ''
        (out/(name+'.vmat')).write_text('"Layer0"\n{\n shader "shaders/forestbase_coating.shader"\n F_SPECULAR "1"\n'+tint+f' g_flCoatingMetalness "{metal}"\n TextureMetalness "[{metal} {metal} {metal} 0]"\n'+''.join(f' Texture{k} "{RESOURCE}/{name}_{v}.png"\n' for k,v in [('Color','color'),('Normal','normal'),('Roughness','rough')])+' TextureAmbientOcclusion "materials/default/default_ao.tga"\n g_flModelTintAmount "1"\n}\n')
    im=Image.new('RGBA',(1024,128));d=ImageDraw.Draw(im)
    for y in (20,55):d.line([(14,y+35),(57,y),(100,y+35)],fill=(194,191,164,255),width=10)
    font=ImageFont.truetype('C:/Windows/Fonts/bahnschrift.ttf',103)
    lettering=Image.new('RGBA',(700,128));ld=ImageDraw.Draw(lettering)
    ld.text((0,-4),'FB / 041',font=font,fill=(194,191,164,255))
    bbox=lettering.getbbox();lettering=lettering.crop(bbox).resize((785,101),Image.Resampling.LANCZOS)
    im.alpha_composite(lettering,(165,12))
    a=np.array(im);a[:,:,3][rng.random((128,1024))<.025]=0
    Image.fromarray(a[:,:,:3]).save(out/'stencil_color.png');Image.fromarray(a[:,:,3]).save(out/'stencil_alpha.png')
    (out/'stencil.vmat').write_text(f'''"Layer0"
{{
 shader "shaders/complex.shader"
 F_ALPHA_TEST "1"
 F_RENDER_BACKFACES "1"
 TextureColor "{RESOURCE}/stencil_color.png"
 TextureTranslucency "{RESOURCE}/stencil_alpha.png"
 TextureNormal "materials/default/default_normal.tga"
 TextureRoughness "[.78 .78 .78 0]"
 g_flAlphaTestReference ".35"
}}
''')
