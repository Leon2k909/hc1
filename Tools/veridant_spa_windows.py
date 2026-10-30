"""Recessed resort spa glazing and shallow, non-traversable 3D room interiors.

Plan coordinates are inches. The original spa block's collision is retained;
only its two visible facade faces are cut around the existing window rectangles.
"""
import math
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

import map_kit as K
import riverdale_parts as P

PREFIX = 'materials/veridant/spa-windows-v2'
NAMES = ('bronze', 'rubber', 'glass', 'linen', 'walnut', 'plaster',
         'plaster_warm', 'wall_art', 'shade', 'shade_off', 'ceramic', 'leaf')
MATERIALS = {f'vr_spa_{name}': f'{PREFIX}/{name}.vmat' for name in NAMES}
X, Y, Z = np.eye(3)


def specifications(rect=(-200., 1200., 760., 1000.)):
    e0, e1, n0, n1 = rect
    rng = np.random.default_rng(3)
    result = []
    for e in np.arange(e0+100, e1-60, 160.):
        result.append(dict(axis='e', at=n0, centre=float(e), width=100.,
                           bottom=250., top=360., lit=bool(rng.random()<.4)))
    for n in np.arange(n0+80, n1-40, 160.):
        result.append(dict(axis='n', at=e0, centre=float(n), width=100.,
                           bottom=200., top=330., lit=bool(rng.random()<.5)))
    return result


def legacy_faces(model, rect=(-200., 1200., 760., 1000.), height=400.):
    """Only the two old facade quads, nine flat pane boxes and eight sills."""
    e0, e1, n0, n1 = rect
    P.card(model, 'vr_stone', [(e0,n0,0),(e1,n0,0),(e1,n0,height),(e0,n0,height)], -Y)
    P.card(model, 'vr_stone', [(e0,n0,0),(e0,n1,0),(e0,n1,height),(e0,n0,height)], -X)
    for spec in specifications(rect):
        c, w, low, high = [spec[k] for k in ('centre','width','bottom','top')]
        paint = 'vr_window_lit' if spec['lit'] else 'vr_window_dark'
        if spec['axis']=='e':
            P.box(model,c-w/2,c+w/2,n0-1.2,n0-.4,low,high,paint)
            P.box(model,c-w/2-4,c+w/2+4,n0-2.5,n0,low-4,low,'vr_stone_light')
        else:
            P.box(model,e0-1.2,e0-.4,c-w/2,c+w/2,low,high,paint)


def washer_faces(model,rect=(-200.,1200.,760.,1000.),old=False):
    """Move the four existing fixture meshes below, rather than over, the glass."""
    from veridant_parts import wall_washer
    n0=rect[2];e0=rect[0]
    for e in (100.,500.,900.):
        wall_washer(model,f'Spa lamp {e}',(e,n0,262. if old else 240.),(0,-1),240,light=False)
    wall_washer(model,'Spa west lamp',(e0,880.,208. if old else 182.),(-1,0),240,light=False)


def facade(model, axis, at, run, height, specs):
    """Continuous original stone UVs, split only at window opening boundaries."""
    holes = [s for s in specs if s['axis']==axis]
    us = sorted({run[0],run[1],*(s['centre']+side*s['width']/2 for s in holes for side in (-1,1))})
    zs = sorted({0.,height,*(s[k] for s in holes for k in ('bottom','top'))})
    def point(u,z): return (u,at,z) if axis=='e' else (at,u,z)
    for u0,u1 in zip(us,us[1:]):
        for z0,z1 in zip(zs,zs[1:]):
            u,z = (u0+u1)/2,(z0+z1)/2
            if any(abs(u-s['centre'])<s['width']/2 and s['bottom']<z<s['top'] for s in holes):
                continue
            P.card(model,'vr_stone',[point(u0,z0),point(u1,z0),point(u1,z1),point(u0,z1)],
                   (0,-1,0) if axis=='e' else (-1,0,0))


def rounded(model, centre, size, paint, bevel=.08):
    P.bevel_box(model,np.array(centre),(X,Y,Z),size,paint,bevel=bevel)


def turned(model, centre, profile, paint, sides=24, caps=True):
    """A rotational profile in height/radius order, smoothly shaded."""
    centre=np.array(centre,float)
    for j,((z0,r0),(z1,r1)) in enumerate(zip(profile,profile[1:])):
        slope=(r1-r0)/max(z1-z0,1e-8)
        for i in range(sides):
            a,b=math.tau*i/sides,math.tau*(i+1)/sides
            ds=[np.array((math.cos(t),math.sin(t),0.)) for t in (a,b)]
            ns=[P.unit(d-Z*slope) for d in ds]
            P.card(model,paint,[centre+ds[0]*r0+Z*z0,centre+ds[1]*r0+Z*z0,
                               centre+ds[1]*r1+Z*z1,centre+ds[0]*r1+Z*z1],sum(ns),
                   normals=(ns[0],ns[1],ns[1],ns[0]))
    if caps:
        for index,normal in ((0,-Z),(-1,Z)):
            z,r=profile[index]
            P.card(model,paint,[centre+np.array((r*math.cos(t),r*math.sin(t),z))
                               for t in np.linspace(0,math.tau,sides,endpoint=False)],normal)


def drape(model, low, high, bottom, top, seed):
    """Pleated linen with a curved hem and smooth fold normals, in room space."""
    phase=seed*.41; segments=max(20,int((high-low)*2)); rows=3
    def point(u,t):
        theta=(u-low)*math.tau/5.6+phase
        hem=bottom+.24*math.sin((u-low)*.9)+.12*math.sin(theta)
        return np.array((u,-17.5+1.45*math.cos(theta)*(1-.08*t),hem+(top-hem)*t))
    for u0,u1 in zip(np.linspace(low,high,segments+1),np.linspace(low,high,segments+1)[1:]):
        for t0,t1 in zip(np.linspace(0,1,rows+1),np.linspace(0,1,rows+1)[1:]):
            pts=[point(u,t) for u,t in ((u0,t0),(u1,t0),(u1,t1),(u0,t1))]
            ns=[]
            for u in (u0,u1,u1,u0):
                theta=(u-low)*math.tau/5.6+phase
                ns.append(P.unit((1.45*math.sin(theta)*math.tau/5.6,1,0)))
            P.card(model,'vr_spa_linen',pts,Y,normals=ns,
                   uv=[(u/12,z/24) for u,d,z in pts],both=True)


def window(model,spec,index):
    """One 100-inch opening: local X across, Y outward, Z up from sill."""
    local=K.Model(); h=spec['top']-spec['bottom']; w=spec['width']; lit=spec['lit']
    # Masonry reveal, a projecting pitched sill and narrow metal profiles.
    for side in (-1,1):
        rounded(local,(side*(w/2-.9),-5,h/2),(1.8,10,h),'vr_stone_light',.16)
    rounded(local,(0,-5,h-1),(w,10,2),'vr_stone_light',.16)
    rounded(local,(0,-2.3,-1.4),(w+6,12.8,2.8),'vr_stone_light',.24)
    # Fine drip groove beneath the outer lip; dark because it is a real recess.
    rounded(local,(0,3.8,-2.72),(w+2,.20,.10),'vr_spa_rubber',.025)
    for u in (-w/2+3,w/2-3):
        rounded(local,(u,-7,h/2),(1.65,3.0,h-4),'vr_spa_bronze',.075)
        rounded(local,(u+(.95 if u<0 else -.95),-5.35,h/2),(.23,.20,h-6),'vr_spa_rubber',.035)
    for z in (2.8,h-2.8):
        rounded(local,(0,-7,z),(w-4.3,3.,1.65),'vr_spa_bronze',.075)
        rounded(local,(0,-5.35,z+(.95 if z<h/2 else -.95)),(w-6.5,.20,.23),'vr_spa_rubber',.035)
    divider=.0 if index%3 else -12.
    rounded(local,(divider,-6.6,h/2),(1.25,2.2,h-6),'vr_spa_bronze',.07)
    transom=h-24.
    rounded(local,(0,-6.6,transom),(w-6.5,2.2,1.10),'vr_spa_bronze',.065)
    # Four independently edged glass panes, with unlit reflective surfaces.
    for u0,u1 in ((-w/2+4.05,divider-.77),(divider+.77,w/2-4.05)):
        for z0,z1 in ((4.05,transom-.67),(transom+.67,h-4.05)):
            pts=[(u0,-6.0,z0),(u1,-6.0,z0),(u1,-6.0,z1),(u0,-6.0,z1)]
            P.card(local,'vr_spa_glass',pts,Y,uv=[((u+w/2)/w,z/h) for u,d,z in pts])
    # Handle and weep slots have a readable construction scale.
    for u in (-24.,24.):rounded(local,(u,-5.39,2.1),(1.1,.10,.12),'vr_spa_rubber',.025)
    handle_u=divider+3.8
    P.rod(local,(handle_u,-4.9,h*.43),(handle_u,-4.9,h*.43+4.2),.19,'vr_spa_bronze',12,True)
    for z in (h*.43,h*.43+4.2):P.rod(local,(handle_u,-6,z),(handle_u,-4.9,z),.16,'vr_spa_bronze',10,True)

    # A shallow 3D room, separated from the glass by curtains and real depth.
    back=-66.; wall='vr_spa_plaster_warm' if lit else 'vr_spa_plaster'
    for side in (-1,1):rounded(local,(side*48,-38,h/2),(2.,56,h-4),wall,.08)
    rounded(local,(0,back,h/2),(96,1.2,h-3),wall,.08)
    rounded(local,(0,-38,.2),(96,56,1.2),'vr_spa_walnut',.08)
    rounded(local,(0,-38,h-1.5),(96,56,1.2),wall,.08)
    # Curtains vary in opening rather than the room switching solid black/white.
    left=16.+(index%3)*5.; right=20.+((index+1)%3)*4.
    drape(local,-45,-45+left,3,h-5,index)
    drape(local,45-right,45,3,h-5,index+7)
    P.rod(local,(-45,-17,h-3),(45,-17,h-3),.33,'vr_spa_bronze',16,True)
    for u in (*np.linspace(-44,-46+left,4),*np.linspace(46-right,44,4)):
        # Visible small suspension rings, not a hovering fabric card.
        P.torus(local,(u,-17,h-4),(1,0,0),.58,.09,'vr_spa_bronze',12,5)
    # Walnut console with softly eased edges and a plaster artwork behind it.
    rounded(local,(0,-51,27),(64,18,2.4),'vr_spa_walnut',.15)
    for u in (-27,27):rounded(local,(u,-52,13),(2.6,12,26),'vr_spa_walnut',.11)
    art_x=-10 if index%2 else 5
    rounded(local,(art_x,-64.7,h*.67),(33,1.2,36),'vr_spa_bronze',.10)
    col,row=index%2,(index//2)%2
    P.card(local,'vr_spa_wall_art',[(art_x-15,-63.95,h*.67-16),(art_x+15,-63.95,h*.67-16),
               (art_x+15,-63.95,h*.67+16),(art_x-15,-63.95,h*.67+16)],Y,
               uv=[((col+u)/2,1-(row+v)/2) for u,v in ((.02,.98),(.98,.98),(.98,.02),(.02,.02))])
    # A lamp is the source of the lit room's warm focus, not the glazing.
    lamp_x=22 if index%2 else -22
    turned(local,(lamp_x,-47,28.3),[(0,3.5),(.45,3.6),(.70,3.2),(1,2.6)],'vr_spa_bronze')
    P.rod(local,(lamp_x,-47,29),(lamp_x,-47,47),.30,'vr_spa_bronze',16,True)
    turned(local,(lamp_x,-47,43),[(0,7.0),(.25,7.0),(12.,4.5),(12.25,4.5)],
           'vr_spa_shade' if lit else 'vr_spa_shade_off',32,caps=False)
    # A solid rim and inner diffuser keep the shade from looking paper-thin.
    for z,r in ((43,7.),(55.2,4.5)):
        P.torus(local,(lamp_x,-47,z),(0,0,1),r,.10,'vr_spa_linen',32,5)
    if lit:
        P.card(local,'vr_spa_shade',[(lamp_x+6.7*math.cos(a),-47+6.7*math.sin(a),43.25)
               for a in np.linspace(0,math.tau,32,endpoint=False)],-Z)
    # Small ceramic vase and foliage are silhouettes beyond the window.
    vase_x=-lamp_x*.82
    turned(local,(vase_x,-50,28.3),[(0,2.8),(.5,3.2),(5,3.5),(8,2.3),(9,2.0)],'vr_spa_ceramic')
    for k in range(7):
        a=k*2.4+index; end=np.array((vase_x+6*math.cos(a),-50+4*math.sin(a),48+(k%3)*2))
        root=np.array((vase_x,-50,35.)); P.rod(local,root,end,.10,'vr_spa_leaf',6)
        axis=P.unit(end-root); side=P.unit(np.cross(axis,Y)); mid=end-axis*3
        P.card(local,'vr_spa_leaf',[end,mid+side*1.2,end-axis*6,mid-side*1.2],Y,both=True)

    out=np.array((0.,-1.,0.)) if spec['axis']=='e' else np.array((-1.,0.,0.))
    right=np.cross(Z,out)
    origin=np.array((spec['centre'],spec['at'],spec['bottom'])) if spec['axis']=='e' else np.array((spec['at'],spec['centre'],spec['bottom']))
    axes=np.array((right,out,Z))
    # The west room stops before the adjacent south-facing room. This is a real
    # geometric separation; no overlapping opaque wall can appear behind its glass.
    def room_point(p):
        p=p.copy()
        if spec['axis']=='n' and p[1]<-10:p[1]=-10+(p[1]+10)*.58
        return p
    def room_normal(n,p):
        n=n.copy()
        if spec['axis']=='n' and p[1]<-10:n[1]/=.58
        return P.unit(n)
    for paint,rows in local.polygons.items():
        for i,(pts,n) in enumerate(rows):
            normals=local.polygon_normals.get((paint,i))
            P.card(model,paint,[origin+room_point(p)@axes for p in pts],room_normal(n,pts[0])@axes,
                   normals=[room_normal(v,p)@axes for v,p in zip(normals,pts)] if normals is not None else None,
                   uv=local.polygon_uvs.get((paint,i)))
    return {'index':index,**spec,'triangles':local.triangle_count(),'recess_inches':6.,
            'room_depth_inches':42.48 if spec['axis']=='n' else 66.}


def build_facades(model,rect=(-200.,1200.,760.,1000.),height=400.):
    e0,e1,n0,n1=rect; specs=specifications(rect)
    facade(model,'e',n0,(e0,e1),height,specs)
    facade(model,'n',e0,(n0,n1),height,specs)
    details=[window(model,spec,i) for i,spec in enumerate(specs)]
    model.material_overrides.update(MATERIALS)
    model.tile_overrides.update({paint:48. for paint in MATERIALS})
    return details


def build_spa(model,rect,height):
    """Generator hook; preserve the original solid block and cap collision."""
    e0,e1,n0,n1=rect
    P.box(model,e0,e1,n0,n1,0,height,
          {'default':'vr_stone','+n':None,'-z':None,'-n':None,'-e':None},'default')
    P.box(model,e0-6,e1+6,n0-6,n1+6,height,height+14,'vr_stone_dark','default')
    return build_facades(model,rect,height)


def write_materials(directory):
    out=Path(directory);out.mkdir(parents=True,exist_ok=True);n=1024
    rng=np.random.default_rng(236071)
    def noise(sigma):
        a=gaussian_filter(rng.normal(size=(n,n)),sigma,mode='wrap');return a/max(a.std(),1e-8)
    fine=noise(.65);broad=noise(22);grain=noise((27,1.3));yy,xx=np.mgrid[0:n,0:n]/n
    def rgb(name,a):Image.fromarray(np.clip(a,0,255).astype('uint8')).save(out/(name+'.png'))
    def grey(name,a):rgb(name,np.asarray(a))
    rgb('bronze_color',(1+.025*broad+.007*fine)[...,None]*np.array((65,58,46)))
    grey('bronze_rough',(.38+.025*broad+.008*fine)*255)
    rgb('walnut_color',(1+.085*grain+.018*broad)[...,None]*np.array((81,64,47)))
    grey('walnut_rough',(.57+.025*grain)*255)
    weave=.008*np.sin(xx*n*math.pi*.74)*np.sin(yy*n*math.pi*.68)+.002*fine
    rgb('linen_color',(1+.025*broad+weave)[...,None]*np.array((185,180,165)))
    gx,gy=np.gradient(weave);normal=np.stack((-gy*4,gx*4,np.ones_like(gx)),axis=-1)
    normal/=np.linalg.norm(normal,axis=-1)[...,None];rgb('linen_normal',(normal*.5+.5)*255)
    grey('glass_rough',(.12+.013*broad+.003*fine)*255)
    # Fine smudges are in roughness, not conspicuous opaque dirt on the pane.
    Image.new('RGB',(16,16),(128,128,255)).save(out/'flat_normal.png')
    # Restrained plaster glow falls around a lamp position, leaving dark corners.
    patch=np.exp(-((xx-.31)/.35)**2-((yy-.46)/.42)**2)
    base=(1+.009*broad+.003*fine)[...,None]*np.array((167,155,135))
    rgb('plaster_color',base)
    rgb('warm_wall_color',base*(.65+.29*patch[...,None]))
    grey('warm_wall_emission',(.08+.50*patch)*255)
    # Abstract spa artwork: real mat surround, ink relief and restrained colours.
    art=np.ones((n,n,3))*np.array((192,184,164))
    sx,sy=np.mod(xx*2,1),np.mod(yy*2,1);variant=(xx*2).astype(int)+(yy*2).astype(int)*2
    mask=(sx>.13)&(sx<.87)&(sy>.13)&(sy<.87)
    palettes=(((86,94,80),(65,75,70),(169,132,78)),((151,116,87),(107,86,66),(110,128,124)),
              ((109,126,130),(64,94,104),(193,163,106)),((168,140,98),(118,106,83),(135,92,66)))
    for k,(near,far,sun) in enumerate(palettes):
        dune=.49+.12*np.sin(sx*(4.8+k*.4)+k*.7)+.035*np.sin(sx*11+k)
        part=mask&(variant==k)
        art[part&(sy>dune)]=near;art[part&(sy>dune+.12)]=far
        disc=((sx-(.65 if k%2==0 else .32))**2+(sy-.32)**2)<.075**2
        art[part&disc]=sun
    rgb('wall_art_color',art*(1+.006*fine[...,None]))
    colours={'rubber':(.055,.057,.052),'ceramic':(.58,.54,.46),'leaf':(.15,.22,.12)}
    for name in NAMES:
        if name=='glass':
            text=('// Tools/veridant_spa_windows.py\n"Layer0"\n{\n'
                  '    shader "shaders/glass.shader"\n    F_GLASS_QUALITY "2"\n'
                  '    g_bFogEnabled "1"\n    g_flBlurAmount "0.015"\n'
                  '    g_flRefractionStrength "1.003"\n    AlbedoAbsorption "0.15"\n'
                  '    g_flTintColor "[1 1 1 0]"\n    TextureColor "[0.85 0.89 0.87 0]"\n'
                  f'    TextureNormal "{PREFIX}/flat_normal.png"\n    TextureRoughness "{PREFIX}/glass_rough.png"\n'
                  '    TextureMetalness "[0 0 0 0]"\n    TextureAmbientOcclusion "[1 1 1 0]"\n'
                  '    TextureBlendMask "materials/default/default_blend.tga"\n'
                  '    TextureTintMask "materials/default/default.tga"\n'
                  '    TextureTranslucency "materials/default/default_trans.tga"\n}\n')
        else:
            texture={'bronze':'bronze_color','walnut':'walnut_color','linen':'linen_color',
                     'plaster':'plaster_color','plaster_warm':'warm_wall_color','wall_art':'wall_art_color',
                     'shade':'linen_color','shade_off':'linen_color'}.get(name)
            colour=f'{PREFIX}/{texture}.png' if texture else 'materials/default/default_color.tga'
            normal=f'{PREFIX}/linen_normal.png' if name in ('linen','shade','shade_off') else f'{PREFIX}/flat_normal.png'
            rough=f'{PREFIX}/bronze_rough.png' if name=='bronze' else f'{PREFIX}/walnut_rough.png' if name=='walnut' else '[0.78 0.78 0.78 0]'
            if name=='linen':rough='[0.94 0.94 0.94 0]'
            tint=colours.get(name,(1,1,1)); metal=.8 if name=='bronze' else 0
            text=('// Tools/veridant_spa_windows.py\n"Layer0"\n{\n    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n'
                  f'    g_flMetalness "{metal}"\n    g_flRoughnessScaleFactor "1"\n'
                  f'    TextureColor "{colour}"\n    TextureNormal "{normal}"\n    TextureRoughness "{rough}"\n'
                  '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n'
                  f'    g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"\n    g_flModelTintAmount "1"\n')
            if name in ('shade','plaster_warm'):
                mask=f'{PREFIX}/warm_wall_emission.png' if name=='plaster_warm' else '[1 1 1 0]'
                strength=.30 if name=='plaster_warm' else .65
                text+=(f'    F_SELF_ILLUM "1"\n    TextureSelfIllumMask "{mask}"\n'
                       f'    g_flSelfIllumBrightness "{strength}"\n    g_flSelfIllumAlbedoFactor "1"\n'
                       '    g_vSelfIllumTint "[1 0.76 0.46 0]"\n')
            text+='}\n'
        (out/(name+'.vmat')).write_text(text)
