"""Closed moulded transport cases with recessed folding handles and hardware."""
import math
from collections import Counter
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter
from scipy.spatial import Delaunay
import map_kit as K
import riverdale_parts as P

PREFIX='materials/veridant/cases-v3'
MATERIALS={f'vr_transport_{name}':f'{PREFIX}/{name}.vmat'
           for name in ('olive','black','rubber','gasket','steel','label')}
X=np.array((1.,0.,0.));Y=np.array((0.,1.,0.));Z=np.array((0.,0.,1.))


def rounded_rect(width,height,radius=1.6):
    points=[];normals=[]
    for sx,sy,start in ((1,1,0),(-1,1,90),(-1,-1,180),(1,-1,270)):
        for angle in np.linspace(start,start+90,5):
            a=math.radians(angle);n=np.array((math.cos(a),math.sin(a)))
            points.append(np.array((sx*(width/2-radius),sy*(height/2-radius)))+radius*n)
            normals.append(n)
    return np.array(points),np.array(normals)


def build_into(model,c,size,along=(1,0),paint='vr_case_black',z0=0.,surface='plastic',seed=0):
    local=K.Model();L,W,H=map(float,size);seam=H*.68;radius=1.6
    shell='vr_transport_olive' if 'olive' in paint else 'vr_transport_black'
    rubber='vr_transport_rubber';steel='vr_transport_steel';gasket='vr_transport_gasket'
    model.material_overrides.update(MATERIALS)
    model.tile_overrides.update({p:12. for p in MATERIALS})

    def card(mat,points,toward,normals=None,uv=None):
        P.card(local,mat,points,toward,normals=normals,uv=uv)

    def box(centre,dimensions,mat=shell,bevel=.12):
        P.bevel_box(local,np.array(centre),(X,Y,Z),dimensions,mat,bevel=bevel)

    def loft(stations,mat=shell,bottom=False,top=False):
        rings=[];shading=[]
        for j,(height,inset) in enumerate(stations):
            xy,ns=rounded_rect(L-2*inset,W-2*inset,radius)
            rings.append([np.array((x,y,height)) for x,y in xy])
            previous=stations[max(0,j-1)];following=stations[min(len(stations)-1,j+1)]
            slope=(following[1]-previous[1])/max(following[0]-previous[0],1e-6)
            shading.append([P.unit((n[0],n[1],slope)) for n in ns])
        for j in range(len(rings)-1):
            for i in range(len(rings[j])):
                k=(i+1)%len(rings[j]);a,b=rings[j][i],rings[j][k]
                card(mat,(a,b,rings[j+1][k],rings[j+1][i]),(a+b)*.5-Z*(a[2]),
                     normals=(shading[j][i],shading[j][k],shading[j+1][k],shading[j+1][i]))
        if bottom:card(mat,rings[0],-Z)
        if top:card(mat,rings[-1],Z)
        return rings

    def inset(height):return .55+(.10-.55)*(height-1)/(seam-.18-1)

    def panel(normal,right,half_depth,half_width,pocket):
        lower,upper=1.,seam-.18;handle_z=H*.415
        span=half_width-radius
        def at(x,height,depth=0.):
            shrink=inset(height)
            return normal*(half_depth-shrink-depth)+right*x*(span-shrink)/span+Z*height
        outer=np.array(((-span,lower),(span,lower),(span,upper),(-span,upper)))
        if not pocket:
            card(shell,[at(x,z) for x,z in outer],normal)
            return
        handle_width=min(9.,half_width*1.1)
        pocket_width=handle_width+3.0;pocket_height=4.9
        hole,_=rounded_rect(pocket_width,pocket_height,.9);hole[:,1]+=handle_z
        vertices=np.vstack((outer,hole));triangles=[]
        def inside(q):
            a=np.abs(q-(0,handle_z))-(np.array((pocket_width,pocket_height))/2-.9)
            return np.linalg.norm(np.maximum(a,0))+min(max(a),0)<.9-1e-7
        for ids in Delaunay(vertices).simplices:
            if not inside(vertices[ids].mean(axis=0)):triangles.append(tuple(ids))
        # A fully constrained boundary is required: no missing panel slivers.
        edges=Counter()
        for ids in triangles:
            for a,b in zip(ids,ids[1:]+ids[:1]):edges[tuple(sorted((a,b)))]+=1
        expected={tuple(sorted((i,(i+1)%4))) for i in range(4)}
        expected.update(tuple(sorted((4+i,4+(i+1)%len(hole)))) for i in range(len(hole)))
        assert {e for e,n in edges.items() if n==1}==expected
        for ids in triangles:
            pts=[at(*vertices[i]) for i in ids]
            uv=[(vertices[i][0]/(2*span)+.5,(vertices[i][1]-lower)/(upper-lower)) for i in ids]
            card(shell,pts,normal,uv=uv)
        rings=[]
        for contraction,depth in ((0.,0.),(.14,.10),(.42,.48),(.63,.66)):
            xy,ns=rounded_rect(pocket_width-2*contraction,pocket_height-2*contraction,max(.28,.9-contraction*.5))
            rings.append(([at(x,z+handle_z,depth) for x,z in xy],ns))
        for j in range(len(rings)-1):
            for i in range(len(hole)):
                k=(i+1)%len(hole)
                points=(rings[j][0][i],rings[j][0][k],rings[j+1][0][k],rings[j+1][0][i])
                outward=normal-right*rings[j][1][i][0]-Z*rings[j][1][i][1]
                card(shell,points,outward)
        card(rubber,rings[-1][0],normal)
        # The handle sits inside its moulded well, with visible pivot bosses.
        mount=normal*(half_depth-inset(handle_z)-.51)+Z*handle_z
        hw=handle_width/2
        for sign in (-1,1):
            pivot=mount+right*sign*hw+Z*.90
            P.rod(local,pivot-right*.32,pivot+right*.32,.29,steel,10,caps=True)
        path=[mount-right*hw+Z*.9,mount-right*(hw+.10)-Z*.30,
              mount-right*(hw-.65)-Z*1.25+normal*.12,
              mount+right*(hw-.65)-Z*1.25+normal*.12,
              mount+right*(hw+.10)-Z*.30,mount+right*hw+Z*.9]
        P.tube(local,path,.37,rubber,sides=8,bend_radius=.55)
        return at

    # Rounded corner strips meet the panel boundaries exactly.
    rings=[];ns=[]
    for height,shrink in ((1.,.55),(seam-.18,.10)):
        xy,normals=rounded_rect(L-2*shrink,W-2*shrink,radius)
        rings.append([np.array((x,y,height)) for x,y in xy]);ns.append(normals)
    for corner in range(4):
        for i in range(corner*5,corner*5+4):
            card(shell,(rings[0][i],rings[0][i+1],rings[1][i+1],rings[1][i]),
                 (rings[0][i]+rings[0][i+1])*.5-Z,
                 normals=[P.unit((n[0],n[1],-.03)) for n in (ns[0][i],ns[0][i+1],ns[1][i+1],ns[1][i])])
    panel(-Y,X,W/2,L/2,True);panel(Y,-X,W/2,L/2,False)
    panel(X,Y,L/2,W/2,True);panel(-X,-Y,L/2,W/2,True)
    loft(((.45,.82),(.73,.59),(1.,.55)),bottom=True)
    card(shell,rings[-1],Z)
    # A closed opaque elastomer gasket replaces the old light-leaking opening.
    loft(((seam-.20,.10),(seam+.19,.10)),gasket,bottom=True,top=True)
    loft(((seam+.13,.10),(seam+.48,0.),(H-.80,0.),(H-.14,.43),(H,.65)),bottom=True,top=True)
    for fraction in (-.29,0.,.29):
        box((L*fraction,0,H+.25),(2.0,W-5.,.50),bevel=.22)
    for sign in (-1,1):
        for fraction in (-.40,.40):
            box((L*fraction,sign*(W/2-.12),seam*.46),(1.35,.62,seam*.72),bevel=.24)
    for sign in (-1,1):
        for other in (-1,1):
            box((sign*(L/2-4),other*(W/2-4),.30),(4.,4.,.60),rubber,.22)
    # Two over-centre catches on the front; pin hinges on the back.
    for sign in (-1,1):
        x=sign*L*.315;y=-W/2-.19
        box((x,y,seam-.12),(3.05,.32,4.7),rubber,.24)
        box((x,y-.24,seam-.55),(1.95,.43,2.75),rubber,.25)
        box((x,y-.20,seam+1.55),(2.3,.34,.75),steel,.15)
        P.rod(local,(x-1.12,y-.48,seam-1.7),(x+1.12,y-.48,seam-1.7),.19,steel,10,caps=True)
        P.tube(local,[(x-.68,y-.51,seam+.4),(x-.68,y-.57,seam+1.65),
                      (x+.68,y-.57,seam+1.65),(x+.68,y-.51,seam+.4)],.105,steel,sides=6,bend_radius=.18)
        for dz in (-1.,1.):box((x,W/2+.05,seam+dz),(2.8,.35,1.30),rubber,.16)
        for a,b in ((-1.35,-.5),(-.38,.38),(.5,1.35)):
            P.rod(local,(x+a,W/2+.30,seam),(x+b,W/2+.30,seam),.26,steel,10,caps=True)
    # Pressure equalisation valve on one end, with a protected ribbed cap.
    valve=np.array((L/2-.13,0.,4.3))
    P.rod(local,valve,valve+X*.40,.65,rubber,16,caps=True)
    P.rod(local,valve+X*.40,valve+X*.52,.45,steel,12,caps=True)
    for offset in (-.22,0.,.22):
        box(valve+X*.54+Y*offset,(.08,.055,.53),rubber,.02)
    label_z=seam-1.45
    label_y=-W/2+inset(label_z)-.025
    x=2.4;z=.62
    card('vr_transport_label',[(-x,label_y,label_z-z),(x,label_y,label_z-z),
                              (x,label_y,label_z+z),(-x,label_y,label_z+z)],-Y,
         uv=((0,1),(1,1),(1,0),(0,0)))
    f=P.unit((along[0],along[1],0.));s=np.cross(Z,f);axes=np.array((f,s,Z));base=np.array((*c,z0))
    for mat,rows in local.polygons.items():
        for index,(points,normal) in enumerate(rows):
            normals=local.polygon_normals.get((mat,index))
            model.polygon(mat,[base+p@axes for p in points],normal=normal@axes,
                          normals=[n@axes for n in normals] if normals is not None else None,
                          uv=local.polygon_uvs.get((mat,index)))
    if surface:model.oriented_box(base+Z*(H/2),(f,s,Z),(L,W,H),{},surface)


def write_materials(directory):
    out=Path(directory);out.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(310417);n=1024
    def noise(sigma):
        a=gaussian_filter(rng.normal(size=(n,n)),sigma,mode='wrap');return a/max(a.std(),1e-8)
    grain=noise(.65);broad=noise(28);smudge=noise(75)
    height=.0009*grain+.0003*noise(1.9)
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))/(2*12/n)
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))/(2*12/n)
    normals=np.stack((-dx,dy,np.ones_like(dx)),axis=-1);normals/=np.linalg.norm(normals,axis=-1)[...,None]
    Image.fromarray(np.clip((normals*.5+.5)*255,0,255).astype('uint8')).save(out/'polymer_normal.png')
    Image.fromarray(np.clip((.82+.025*grain+.035*smudge)*255,0,255).astype('uint8')).save(out/'polymer_rough.png')
    for name,colour in (('olive',(75.,84.,61.)),('black',(35.,38.,37.))):
        shade=1+.014*broad+.012*grain+.008*smudge
        Image.fromarray(np.clip(shade[...,None]*colour,0,255).astype('uint8')).save(out/f'{name}_color.png')
    Image.new('RGB',(16,16),(128,128,255)).save(out/'flat_normal.png')
    Image.new('L',(16,16),205).save(out/'flat_rough.png')
    label=Image.new('RGB',(768,200),(178,181,164));draw=ImageDraw.Draw(label)
    font_path='C:/Windows/Fonts/consola.ttf'
    font=ImageFont.truetype(font_path,34);small=ImageFont.truetype(font_path,22)
    draw.rectangle((9,9,758,190),outline=(41,48,39),width=3)
    draw.text((29,18),'VERIDANT  /  FIELD EQUIPMENT',font=font,fill=(34,42,33))
    draw.text((30,65),'TRANSPORT  /  SEALED  /  VR-042',font=small,fill=(40,47,38))
    for x in range(31,520,7):
        if rng.random()>.24:draw.rectangle((x,107,x+int(rng.integers(1,5)),166),fill=(40,46,37))
    draw.text((559,111),'042-A',font=font,fill=(34,42,33));label.save(out/'label_color.png')
    specs={'olive':('olive',(1,1,1),0),'black':('black',(1,1,1),0),
           'rubber':(None,(.085,.092,.087),0),'gasket':(None,(.038,.043,.036),0),
           'steel':(None,(.21,.235,.22),.78),'label':('label',(1,1,1),0)}
    for name,(texture,tint,metal) in specs.items():
        colour=f'{PREFIX}/{texture}_color.png' if texture else 'materials/default/default_color.tga'
        normal=f'{PREFIX}/polymer_normal.png' if name in ('olive','black','rubber') else f'{PREFIX}/flat_normal.png'
        rough=f'{PREFIX}/polymer_rough.png' if name in ('olive','black','rubber') else f'{PREFIX}/flat_rough.png'
        exponent='.65' if name=='steel' else '1'
        text=('// Tools/veridant_transport_case.py\n"Layer0"\n{\n'
              '    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n'
              f'    g_flRoughnessScaleFactor "{exponent}"\n    g_flMetalness "{metal}"\n'
              f'    TextureColor "{colour}"\n    TextureNormal "{normal}"\n    TextureRoughness "{rough}"\n'
              '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n'
              f'    g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"\n    g_flModelTintAmount "1.0"\n}}\n')
        (out/f'{name}.vmat').write_text(text)
