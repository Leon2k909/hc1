"""Reference FB/027 six-wheel transport truck. Visual replacement only.
The original truck builder supplies unchanged collision; no scene or runtime edits.
"""
import math
from pathlib import Path
from collections import defaultdict
import numpy as np
from PIL import Image,ImageDraw,ImageFont,ImageFilter
import map_kit as K

RESOURCE='materials/forestbase/truck'
SPECS={'paint':((88,94,63),.72,.08),'metal':((64,67,57),.60,.65),
 'rubber':((43,41,34),.88,0),'canvas':((87,91,60),.86,0),
 'webbing':((104,97,73),.83,0),'glass':((29,37,39),.25,.25),
 'perforated':((56,58,52),.63,.65)}

def configure(m):
    for name in (*SPECS,'stencil','amber','red','lamp'):
        m.material_overrides['truck_'+name]=f'{RESOURCE}/{name}.vmat'
        m.tile_overrides['truck_'+name]=80 if name=='paint' else 32

def refine(m,api):
    configure(m)
    if isinstance(m,api['CollisionOnlyModel']):return
    out=K.Model();configure(out)
    def face(pts,p='paint',normal=None,uv=None,normals=None):
        pts=[np.array(q,float) for q in pts]
        if normal is not None and np.dot(np.cross(pts[1]-pts[0],pts[2]-pts[0]),normal)<0:
            pts.reverse()
            if uv is not None:uv=list(reversed(uv))
            if normals is not None:normals=list(reversed(normals))
        if uv is None and p in ('paint','metal','glass'):
            norm=np.cross(pts[1]-pts[0],pts[2]-pts[0]);axis=int(np.argmax(abs(norm)))
            axes=(1,2) if axis==0 else (0,2) if axis==1 else (0,1)
            low=np.min(pts,axis=0);size=np.maximum(np.max(pts,axis=0)-low,.001)
            uv=[tuple((q[a]-low[a])/size[a] for a in axes) for q in pts]
        out.polygon('truck_'+p,pts,uv=uv,normals=normals)
    def block(a,b,p='paint',r=.45):
        t=K.Model();api['bevel_box'](t,a,b,'part',r)
        for pts,n in t.polygons['part']:
            axis=int(np.argmax(abs(n)));axes=(1,2) if axis==0 else (0,2) if axis==1 else (0,1)
            coords=[tuple((q[k]-a[k])/(b[k]-a[k]) for k in axes) for q in pts]
            face(pts,p,uv=coords)
    def rod(a,b,r=.6,p='metal',segments=8):api['tube'](out,a,b,r,'truck_'+p,segments=segments)
    def bolt(c,axis=(0,0,1),r=.55):
        c=np.array(c,float);rod(c,c+np.array(axis)*.45,r,segments=6)
    def handle(a,b,up=(0,0,2),r=.45):
        a=np.array(a);b=np.array(b);v=np.array(up);rod(a,a+v,r);rod(a+v,b+v,r);rod(b+v,b,r)
    def ring(c,r=1,axis=(0,1,0),p='metal',width=.22):
        c=np.array(c);axis=K.normalise(axis);u=np.array((1,0,0));v=np.cross(axis,u)
        for a,b in zip(np.linspace(0,math.tau,13)[:-1],np.linspace(0,math.tau,13)[1:]):
            pts=[c+(u*math.cos(t)+v*math.sin(t))*rr for t,rr in ((a,r),(b,r),(b,r-width),(a,r-width))]
            face(pts,p,normal=axis)
    def sidepanel(side,x0,x1,z0,z1,p,yy,uv=True):
        # Bottom-to-top UVs remain readable on both sides of the vehicle.
        xs=(x1,x0) if side>0 else (x0,x1)
        pts=[(xs[0],yy(z0),z0),(xs[1],yy(z0),z0),(xs[1],yy(z1),z1),(xs[0],yy(z1),z1)]
        face(pts,p,uv=((0,0),(1,0),(1,1),(0,1)) if uv else None)
    # Chassis, raised cargo deck and inboard cab core.
    block((-140,-40,25),(132,40,36),'metal',.7)
    block((-139,-44,37),(41,44,50),r=1.1)
    block((48,-38,37),(134,38,82),r=1.5)
    temp=K.Model()
    api['loft'](temp,[[(48,-45,82),(134,-45,82),(134,45,82),(48,45,82)],
                      [(50,-42,119),(114,-42,119),(114,42,119),(50,42,119)]],'part')
    for pts,norm in temp.polygons['part']:face(pts)
    block((48,-44,118),(116,44,122),r=1)
    for side in (-1,1):
        y=lambda zz:side*(45-(zz-82)*3/37+.32)
        # Side skin is cut around the front tire rather than covering it.
        outline=[(48,39),(63,39),(65,36),(76,52),(110,52),(122,37),(134,37),(134,82),(48,82)]
        # Quads above a sampled lower edge avoid triangulating a concave arch.
        lower=[(48,39),(63,39),(65,36),(76,52),(110,52),(122,37),(134,37)]
        for (xa,za),(xb,zb) in zip(lower,lower[1:]):
            pts=[(xa,side*45,za),(xb,side*45,zb),(xb,side*45,82),(xa,side*45,82)]
            face(pts,normal=(0,side,0),uv=[((x-48)/86,(zz-37)/45) for x,_,zz in pts])
        # Separate rear quarter pane and driver pane with substantial seals.
        for pts in [[(54,y(85.5),85.5),(78,y(85.5),85.5),(78,y(115),115),(54,y(115),115)],
                    [(82,y(85.5),85.5),(127,y(85.5),85.5),(111,y(115),115),(82,y(115),115)]]:
            face(pts,'rubber',normal=(0,side,.1))
            center=np.mean(pts,axis=0)
            glass=[center+(np.array(p)-center)*.935+np.array((0,side*.13,0)) for p in pts]
            face(glass,'glass',normal=(0,side,.1))
            for k in range(4):rod(pts[k],pts[(k+1)%4],.32,'metal',8)
        # Cab doors, shut lines, handles and hinges.
        for xa,xb in ((51,79),(81,129)):
            for zz in (81,):rod((xa,side*45.3,zz),(xb,side*45.3,zz),.22,'metal',6)
            rod((xa,side*45.4,56),(xa,side*45.4,81),.22,'metal',6)
        for zz in (59,76):
            block((125,min(side*45.3,side*46.3),zz),(128,max(side*45.3,side*46.3),zz+3),'metal',.25)
            bolt((126.5,side*46.5,zz+1.5),(0,side,0),.4)
        block((56,min(side*45.3,side*46.3),72),(69,max(side*45.3,side*46.3),75),'rubber',.6)
        handle((58,side*46.7,74),(67,side*46.7,74),up=(0,side*1.1,0),r=.55)
        sidepanel(side,87,119,54,77,'stencil',lambda zz:side*45.55)
        for xx in (52,80,129):
            for zz in (80,116):bolt((xx,y(zz)+side*.45,zz),(0,side,.1),.42)
        # Angular front wheel protector: solid top and a folded outer lip.
        outer=[(-29,2),(-29,13),(-17,30),(17,30),(29,13),(29,2)]
        inner=[(-25,3),(-25,11),(-15,25),(15,25),(25,11),(25,3)]
        for k in range(5):
            face([(93+x,side*58,22+zz) for x,zz in (outer[k],outer[k+1],inner[k+1],inner[k])],normal=(0,side,0))
            face([(93+x,yy,22+zz) for (x,zz),yy in ((outer[k],side*41),(outer[k+1],side*41),(outer[k+1],side*58),(outer[k],side*58))],normal=(0,0,1))
        # Two perforated entry steps and grab rail behind the door.
        for zz,xx in ((25,47),(34,48)):
            block((xx,min(side*43,side*56),zz),(xx+18,max(side*43,side*56),zz+2),'metal',.5)
            sidepanel(side,xx+1,xx+17,zz+.2,zz+1.5,'perforated',lambda z:side*56.15)
        handle((50,side*45.8,48),(50,side*45.8,78),up=(0,side*2,0),r=.65)
        # Mirror housing, recessed reflective face and two braced arms.
        rod((113,y(104),104),(110,side*59,112),.85)
        rod((111,y(116),116),(110,side*59,116),.65)
        block((106,min(side*59,side*62),101),(112,max(side*59,side*62),119),'rubber',1.2)
        sidepanel(side,107,111,102,118,'glass',lambda zz:side*62.1)
    # Split windshield with rim, pivots and swept wiper blades.
    def windshield(yy,zz,off=.4):return (134-(zz-82)*20/37+off,yy,zz)
    for ya,yb in ((-40,-1.2),(1.2,40)):
        pts=[windshield(ya,85.5),windshield(yb,85.5),windshield(yb*.93,115),windshield(ya*.93,115)]
        face(pts,'rubber',normal=(1,0,.5))
        center=np.mean(pts,axis=0);face([center+(np.array(p)-center)*.94+np.array((.15,0,.08)) for p in pts],'glass',normal=(1,0,.5))
        for k in range(4):rod(pts[k],pts[(k+1)%4],.4)
    for yy in (-22,22):
        rod(windshield(yy,86,1),windshield(yy-10,100,1),.35,'metal')
        rod(windshield(yy-15,95,1.5),windshield(yy-8,109,1.5),.55,'rubber')
        bolt(windshield(yy,86,1.1),(1,0,.4),.75)
    # Nose grille, lamps, tow points and protective bumper/cage.
    block((134,-23,48),(135.4,23,76),'rubber',.6)
    for zz in np.arange(50,75,3):block((135.5,-21,zz),(136.4,21,zz+1.1),'metal',.18)
    block((132,-49,35),(141,49,44),'metal',1)
    for yy in (-34,34):
        block((134,yy-9,51),(138,yy+9,69),'metal',1)
        block((138.1,yy-6,55),(138.5,yy+6,66),'lamp',.4)
        block((138.3,yy-8,51),(138.7,yy-5,58),'amber',.3)
        for zz in (53,67):rod((139,yy-8,zz),(139,yy+8,zz),.6)
        handle((141,yy-5,37),(141,yy+5,37),up=(2.5,0,0),r=1)
    for yy in (-47,47):rod((142,yy,43),(142,yy,78),1.2)
    rod((142,-47,78),(142,47,78),1.1)
    # Roof luggage cage, secured transit case and small warning beacon.
    block((59,-24,122),(106,24,124),'metal',.65)
    block((62,-21,124),(103,21,138),r=1.5)
    for xx in (66,98):
        for yy in (-22,22):block((xx-1,yy-.6,125),(xx+1,yy+.6,138),'metal',.25)
        rod((xx,-22,138.3),(xx,22,138.3),.55,'webbing')
    for xx in (59,106):
        for yy in (-25,25):rod((xx,yy,123),(xx,yy,140),.6)
        rod((xx,-25,140),(xx,25,140),.6)
    for yy in (-25,25):rod((59,yy,140),(106,yy,140),.6)
    rod((109,32,122),(109,32,124),2.7)
    rod((109,32,124),(109,32,130),2.1,'amber',20)
    # Cargo drop-sides: four slatted gates and their hinges under the canvas.
    for side in (-1,1):
        for left,right in zip((-139,-94,-49,-4),(-94,-49,-4,41)):
            block((left,min(side*43.7,side*44.5),50),(right,max(side*43.7,side*44.5),68),r=.3)
            for zz in (53,59,65):
                block((left+1,min(side*44.6,side*45.4),zz),(right-1,max(side*44.6,side*45.4),zz+2.8),r=.28)
            for xx in (left+2,right-2):
                for zz in (54,65):bolt((xx,side*45.9,zz),(0,side,0),.45)
            block((left+4,min(side*45.3,side*46.2),49),(left+12,max(side*45.3,side*46.2),52),'metal',.3)
        for xx in (-139,-94,-49,-4,41):block((xx-1.4,min(side*43.8,side*46),48),(xx+1.4,max(side*43.8,side*46),68),'metal',.35)
    # Drape over the existing five bows; the lower side boards stay exposed.
    def cloth(s,u):
        x=-139+180*s
        if u<.2:y,z=-44,68+45*u/.2
        elif u>.8:y,z=44,113-45*(u-.8)/.2
        else:a=((u-.2)/.6-.5)*math.pi;y,z=44*math.sin(a),113+17*math.cos(a)
        sag=math.sin((x+133)/41*math.pi)**2;side=min(1,abs(y)/44)**4
        fold=(1.9*sag+1.0*math.sin(z*.2+x*.12))*side*math.sin((z-68)/62*math.pi)
        fold+=.9*math.sin(x*.52)*math.exp(-max(0,z-68)/10)*side
        y+=(1 if y>=0 else -1)*fold;z-=2.6*sag*(1-side)
        return np.array((x,y,z))
    def cn(s,u):return K.normalise(np.cross(cloth(s+.0001,u)-cloth(s-.0001,u),cloth(s,u+.0001)-cloth(s,u-.0001)))
    for a in range(64):
        for b in range(48):
            coords=[(a/64,b/48),((a+1)/64,b/48),((a+1)/64,(b+1)/48),(a/64,(b+1)/48)]
            # Fit one cloth image to the cover. Repeating the nonperiodic dirt
            # image caused visible horizontal and vertical texture seams.
            face([cloth(s,u) for s,u in coords],'canvas',uv=coords,normals=[cn(s,u) for s,u in coords])
    for s in (0,1):
        pts=[cloth(s,u) for u in np.linspace(0,1,41)]
        center=np.array((-139+180*s,0,94))
        # An interior fan also handles the slightly concave hem wrinkles.
        for k in range(len(pts)):
            tri=[center,pts[k],pts[(k+1)%len(pts)]]
            face(tri,'canvas',normal=(-1,0,0) if s==0 else (1,0,0),uv=[(p[1]/88+.5,(p[2]-68)/62) for p in tri])
    for x in (-133,-92,-51,-10,35):
        s=(x+139)/180
        for k in range(48):
            coords=[(s-1.35/180,k/48),(s+1.35/180,k/48),(s+1.35/180,(k+1)/48),(s-1.35/180,(k+1)/48)]
            face([cloth(ss,u)+cn(ss,u)*.36 for ss,u in coords],'webbing',uv=[(0,k/48),(1,k/48),(1,(k+1)/48),(0,(k+1)/48)],normals=[cn(ss,u) for ss,u in coords])
        for side in (-1,1):
            for zz in (76,98,113):
                y=side*45.8
                for z2 in (zz-1.3,zz+1.3):rod((x-2,y,z2),(x+2,y,z2),.28)
                for x2 in (x-2,x+2):rod((x2,y,zz-1.3),(x2,y,zz+1.3),.28)
            block((x-1.2,min(side*44.5,side*45.5),57),(x+1.2,max(side*44.5,side*45.5),69),'webbing',.2)
            handle((x-2,side*46,61),(x+2,side*46,61),up=(0,side*.8,0),r=.3)
    for side in (-1,1):
        for x in np.arange(-130,40,14):
            ring((x,side*45.1,69),.9,(0,side,0),width=.25)
            rod((x,side*45.5,68),(x+3,side*45.5,64),.2,'webbing',6)
    # Real exhaust outlet and perforated heat shield behind the cab.
    rod((43,44,47),(43,48,62),2.5)
    rod((43,48,62),(43,48,132),2.7)
    for k in range(32):
        a,b=math.tau*k/32,math.tau*(k+1)/32
        face([(43+4.2*math.cos(t),48+4.2*math.sin(t),zz) for t,zz in ((a,73),(b,73),(b,111),(a,111))],
             'perforated',uv=[(a/math.tau,0),(b/math.tau,0),(b/math.tau,2),(a/math.tau,2)],
             normals=[(math.cos(t),math.sin(t),0) for t in (a,b,b,a)])
        face([(43+2.7*math.cos(t),48+2.7*math.sin(t),zz+math.cos(t)*.7) for t,zz in ((a,131),(b,131),(b,143),(a,143))],
             'metal',normals=[(math.cos(t),math.sin(t),0) for t in (a,b,b,a)])
    for zz in (74,110):ring((43,48,zz),4.4,(0,0,1),width=.4)
    # Tanks, storage locker, axles and leaf springs.
    for side in (-1,1):
        ya,yb=sorted((side*35,side*48))
        block((-10,ya,22),(32,yb,42),r=1.3)
        for zz in (27,38):bolt((27,side*48.3,zz),(0,side,0),.6)
        block((5,min(side*48,side*49),31),(10,max(side*48,side*49),37),'metal',.3)
        for xx in (-104,-45,93):
            for j in range(3):block((xx-15+j*2,min(side*30,side*34),23-j*1.4),(xx+15-j*2,max(side*30,side*34),24-j*1.4),'metal',.2)
    for x in (-104,-45,93):
        rod((x,-48,22),(x,48,22),3.1)
        for side in (-1,1):
            w=api['model']();api['wheel'](w,x,side*48,22)
            for p,faces in w.polygons.items():
                target='rubber' if p=='rubber' else 'metal'
                for i,(pts,n) in enumerate(faces):
                    out.polygon('truck_'+target,pts,normal=n,normals=w.polygon_normals.get((p,i)))
            for a in np.linspace(0,math.tau,28,endpoint=False):
                for row in (-1,1):
                    tangent=(-math.sin(a),0,math.cos(a));radial=(math.cos(a),0,math.sin(a))
                    out.oriented_box((x+21.1*math.cos(a),side*48+row*5.1,22+21.1*math.sin(a)),(tangent,(0,-1,0),radial),(3.2,2.7,1.2),'truck_rubber')
    for yy in (-33,33):
        block((-142,yy-6,46),(-139,yy+6,58),'metal',.5)
        block((-142.3,yy-5,48),(-142.05,yy+5,53),'red',.2)
        block((-142.3,yy-5,54),(-142.05,yy+5,57),'amber',.2)
    # Replace only visual buffers; keep the old authored physics verbatim.
    m.polygons=out.polygons;m.polygon_uvs=out.polygon_uvs;m.polygon_normals=out.polygon_normals
    configure(m)

def materials(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True);rng=np.random.default_rng(23027);n=1024
    y,x=np.mgrid[:n,:n];cloud=np.zeros((n,n))
    for k in (8,16,32,64):cloud+=(np.asarray(Image.fromarray(rng.integers(0,255,(k,k),dtype=np.uint8)).resize((n,n),Image.Resampling.BICUBIC),float)-127)/(k**.25)
    cloud/=max(cloud.std(),1);fine=rng.normal(0,1,(n,n))
    for name,(base,rough,metal) in SPECS.items():
        color=np.clip(np.array(base)[None,None,:]+cloud[:,:,None]*4+fine[:,:,None]*1.2,0,255).astype('uint8')
        im=Image.fromarray(color);d=ImageDraw.Draw(im);height=fine*.0008
        if name in ('paint','metal'):
            for k in range(5000):
                edge=int(rng.integers(4));p=float(rng.uniform(3,n-3));depth=float(rng.exponential(11)+3)
                xx,yy=(p,depth) if edge==0 else (p,n-depth) if edge==1 else (depth,p) if edge==2 else (n-depth,p)
                dx,dy=(float(rng.uniform(1,15)),float(rng.uniform(1,3))) if edge<2 else (float(rng.uniform(1,3)),float(rng.uniform(1,15)))
                d.rectangle((xx,yy,xx+dx,yy+dy),fill=(125,121,100) if k%3 else (36,39,31))
            for k in range(1100):
                xx,yy=rng.integers(20,n-20,2);r=float(rng.uniform(1,5));d.ellipse((xx,yy,xx+r,yy+r*.6),fill=(43,46,33) if k%3 else (121,119,98))
        if name in ('canvas','webbing'):
            cloth=(np.sin(x*math.pi*.67)+np.sin(y*math.pi*.67))*.0009
            height+=cloth+cloud*.0012
            arr=np.asarray(im).astype(float);arr*= (1+cloud*.06+np.sin(x*.04+y*.015)*.015)[:,:,None]
            im=Image.fromarray(np.clip(arr,0,255).astype('uint8'))
        if name=='glass':
            im=Image.fromarray(np.clip(np.array(base)[None,None,:]+cloud[:,:,None]*2+fine[:,:,None]*.5,0,255).astype('uint8'));height*=.02
            gd=ImageDraw.Draw(im)
            for k in range(48):
                xx=int(rng.integers(n));gd.line((xx,0,xx+int(rng.integers(-30,30)),n),fill=(38,43,40),width=int(rng.integers(1,4)))
        if name=='perforated':
            im=Image.new('RGB',(n,n),(67,68,59));pd=ImageDraw.Draw(im)
            for row,yy in enumerate(range(-10,n+20,32)):
                for xx in range(-20,n+20,32):
                    xx+=16 if row%2 else 0;pd.ellipse((xx,yy,xx+17,yy+17),fill=(20,23,21));pd.arc((xx,yy,xx+18,yy+18),0,180,fill=(111,109,94),width=2)
            height=np.asarray(im).mean(axis=2)*.0008
        im.save(out/(name+'_color.png'),compress_level=4)
        dy,dx=np.gradient(height*3);norm=np.stack((-dx,-dy,np.ones_like(dx)),axis=-1);norm/=np.linalg.norm(norm,axis=-1,keepdims=True)
        Image.fromarray(np.clip((norm*.5+.5)*255,0,255).astype('uint8')).save(out/(name+'_normal.png'),compress_level=4)
        rr=np.clip(rough+cloud*.025,.2,.96);Image.fromarray((rr*255).astype('uint8')).convert('RGB').save(out/(name+'_rough.png'),compress_level=4)
        (out/(name+'.vmat')).write_text('"Layer0"\n{\n shader "shaders/forestbase_coating.shader"\n F_SPECULAR "1"\n'+f' TextureColor "{RESOURCE}/{name}_color.png"\n TextureNormal "{RESOURCE}/{name}_normal.png"\n TextureRoughness "{RESOURCE}/{name}_rough.png"\n TextureAmbientOcclusion "materials/default/default_ao.tga"\n g_flCoatingMetalness "{metal}"\n g_flModelTintAmount "1"\n}}\n')
    im=Image.new('RGBA',(512,512));d=ImageDraw.Draw(im);font=ImageFont.truetype('C:/Windows/Fonts/consolab.ttf',66)
    for yy in (54,107):d.polygon([(142,yy+60),(256,yy),(370,yy+60),(370,yy+93),(256,yy+35),(142,yy+93)],fill=(214,211,186,245))
    d.text((42,290),'FB / 027',font=font,fill=(212,210,185,245))
    a=np.array(im);a[:,:,3][rng.random((512,512))<.04]=0;Image.fromarray(a[:,:,:3]).save(out/'stencil_color.png');Image.fromarray(a[:,:,3]).save(out/'stencil_alpha.png')
    (out/'stencil.vmat').write_text(f'''"Layer0"
{{
 shader "shaders/complex.shader"
 F_ALPHA_TEST "1"
 F_RENDER_BACKFACES "1"
 TextureColor "{RESOURCE}/stencil_color.png"
 TextureTranslucency "{RESOURCE}/stencil_alpha.png"
 TextureNormal "materials/default/default_normal.tga"
 TextureRoughness "[.8 .8 .8 0]"
 g_flAlphaTestReference ".35"
}}
''')
    for name,c,bright in [('amber','1 .45 .035',.35),('red','.35 .02 .008',0),('lamp','.9 .94 1',1.2)]:
        (out/(name+'.vmat')).write_text('"Layer0"\n{\n shader "shaders/complex.shader"\n F_SPECULAR "1"\n F_SELF_ILLUM "1"\n'+f' TextureColor "[{c} 0]"\n TextureSelfIllumMask "[1 1 1 0]"\n g_flSelfIllumBrightness "{bright}"\n g_flSelfIllumAlbedoFactor "1"\n g_vSelfIllumTint "[1 1 1 0]"\n TextureNormal "materials/default/default_normal.tga"\n TextureRoughness "[.7 .7 .7 0]"\n}}\n')
