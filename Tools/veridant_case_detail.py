"""Moulded equipment cases: formed panels, protected hardware and stacking trays.

All dimensions are inches. The existing collision footprint and stack pitch are
retained; broad structural forms belong to the shell, rather than floating ribs.
"""
from collections import Counter
from pathlib import Path
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter
from scipy.spatial import Delaunay
import map_kit as K
import riverdale_parts as P

PREFIX = 'materials/veridant/cases-v4'
NAMES = ('olive', 'black', 'olive_edge', 'black_edge', 'rubber', 'gasket',
         'steel', 'alloy', 'label')
MATERIALS = {f'vr_transport_{name}': f'{PREFIX}/{name}.vmat' for name in NAMES}
X = np.array((1., 0., 0.)); Y = np.array((0., 1., 0.)); Z = np.array((0., 0., 1.))


def rounded_rect(width, height, radius, steps=4):
    radius = min(radius, min(width, height) * .48)
    points = []; normals = []
    for sx, sy, start in ((1, 1, 0), (-1, 1, 90), (-1, -1, 180), (1, -1, 270)):
        for angle in np.linspace(start, start + 90, steps + 1):
            a = math.radians(angle); n = np.array((math.cos(a), math.sin(a)))
            points.append((sx * (width / 2 - radius), sy * (height / 2 - radius)) + radius * n)
            normals.append(n)
    return np.array(points), np.array(normals)


def _inside(point, polygon):
    """Strict containment in a convex counterclockwise contour."""
    delta = np.roll(polygon, -1, axis=0) - polygon
    q = point - polygon
    return bool(np.all(delta[:, 0] * q[:, 1] - delta[:, 1] * q[:, 0] > 1e-7))


def triangulate(outer, holes=()):
    """Triangulate a panel, proving every outside and pocket edge survives."""
    contours = [np.asarray(outer), *(np.asarray(p) for p in holes)]
    vertices = np.vstack(contours); rows = []
    for ids in Delaunay(vertices).simplices:
        centre = vertices[ids].mean(axis=0)
        if not any(_inside(centre, hole) for hole in holes):
            rows.append(tuple(map(int, ids)))
    edges = Counter()
    for ids in rows:
        for a, b in zip(ids, ids[1:] + ids[:1]):
            edges[tuple(sorted((a, b)))] += 1
    expected = set(); offset = 0
    for contour in contours:
        expected.update(tuple(sorted((offset + i, offset + (i + 1) % len(contour)))) for i in range(len(contour)))
        offset += len(contour)
    assert {edge for edge, count in edges.items() if count == 1} == expected, 'Panel boundary is not constrained.'
    assert max(edges.values()) <= 2
    return vertices, rows


def build_into(model, c, size, along=(1, 0), paint='vr_case_black', z0=0., surface='plastic', seed=0):
    local = K.Model(); L, W, H = map(float, size)
    seam = H * .735; radius = 2.5
    shell = 'vr_transport_olive' if 'olive' in paint else 'vr_transport_black'
    rim = shell + '_edge'
    rubber = 'vr_transport_rubber'; gasket = 'vr_transport_gasket'
    steel = 'vr_transport_steel'; alloy = 'vr_transport_alloy'
    model.material_overrides.update(MATERIALS)
    model.tile_overrides.update({p: 16. for p in MATERIALS})

    def card(mat, points, toward, normals=None, uv=None):
        P.card(local, mat, points, toward, normals=normals, uv=uv)

    def box(centre, dimensions, mat=steel, bevel=.10, axes=(X, Y, Z)):
        P.bevel_box(local, np.array(centre), axes, dimensions, mat, bevel=bevel)

    def screw(at, normal, right=X, r=.115):
        at = np.asarray(at)
        P.lathe_axis(local, at, normal, ((r*.78, 0), (r, .025), (r, .07), (r*.78, .095)),
                     alloy, sides=8, cap=alloy)
        # A recessed drive gives the screw head a readable centre.
        P.rod(local, at + normal*.10 - right*r*.54, at + normal*.10 + right*r*.54,
              .022, gasket, 4, caps=True)

    def loft(stations, mat=shell, bottom=False, top=False):
        rings = []; shade = []
        for j, (height, shrink) in enumerate(stations):
            xy, ns = rounded_rect(L-2*shrink, W-2*shrink, radius)
            rings.append([np.array((x, y, height)) for x, y in xy])
            prev = stations[max(j-1, 0)]; nxt = stations[min(j+1, len(stations)-1)]
            slope = (nxt[1]-prev[1]) / max(nxt[0]-prev[0], 1e-6)
            shade.append([P.unit((n[0], n[1], slope)) for n in ns])
        for j in range(len(rings)-1):
            for i in range(len(rings[j])):
                k = (i+1) % len(rings[j])
                card(mat, (rings[j][i], rings[j][k], rings[j+1][k], rings[j+1][i]),
                     np.array((*P.unit(rings[j][i][:2]+rings[j][k][:2]), 0.)),
                     normals=(shade[j][i], shade[j][k], shade[j+1][k], shade[j+1][i]))
        if bottom: card(mat, rings[0], -Z)
        if top: card(mat, rings[-1], Z)
        return np.array(rings)

    def formed_recess(origin, right, up, out, width, height, r, depth, mat=shell, backing=None):
        """Continuous rounded moulded shoulder into a recessed field."""
        origin = np.asarray(origin); rings = []; normals = []
        profiles = ((0., 0., 0.), (.12, .07, .65), (.34, depth-.08, .65), (.48, depth, 0.))
        for inset, d, slope in profiles:
            xy, ns = rounded_rect(width-2*inset, height-2*inset, max(.18, r-inset))
            rings.append([origin + right*x + up*y - out*d for x, y in xy])
            normals.append([P.unit(out-(right*n[0]+up*n[1])*slope) for n in ns])
        for j in range(len(rings)-1):
            for i in range(len(rings[j])):
                k = (i+1) % len(rings[j])
                card(mat, (rings[j][i], rings[j][k], rings[j+1][k], rings[j+1][i]), out,
                     normals=(normals[j][i], normals[j][k], normals[j+1][k], normals[j+1][i]))
        if backing: card(backing, rings[-1], out)
        return np.array(rings[-1]), np.array(rings[0])

    # The main vertical faces taper slightly toward a radiused plinth.
    body_low = 1.4; body_high = seam-.26
    inset_low = .74; inset_high = .46
    def inset(z):
        return inset_low + (inset_high-inset_low)*(z-body_low)/(body_high-body_low)

    # Corner strips join the formed face panels without duplicated wall faces.
    rings=[]; corner_normals=[]
    for height, shrink in ((body_low, inset_low), (body_high, inset_high)):
        xy, ns = rounded_rect(L-2*shrink, W-2*shrink, radius)
        rings.append([np.array((x, y, height)) for x, y in xy]); corner_normals.append(ns)
    for corner in range(4):
        for i in range(corner*5, corner*5+4):
            card(shell, (rings[0][i], rings[0][i+1], rings[1][i+1], rings[1][i]),
                 np.array((*corner_normals[0][i], 0.)),
                 normals=[P.unit((*n, .018)) for n in (corner_normals[0][i], corner_normals[0][i+1],
                                                      corner_normals[1][i+1], corner_normals[1][i])])

    def face(normal, right, half_depth, half_width, handle=True):
        span = half_width-radius
        def at(x, z, depth=0.):
            shrink = inset(z)
            return normal*(half_depth-shrink-depth) + right*x*(span-shrink)/span + Z*z
        outer = np.array(((-span, body_low), (span, body_low), (span, body_high), (-span, body_high)))
        field_width=2*span-3.2; field_height=body_high-body_low-2.4
        middle=(body_low+body_high)/2
        field, _ = rounded_rect(field_width, field_height, 1.2)
        field[:, 1] += middle
        vertices, triangles=triangulate(outer, (field,))
        for ids in triangles:
            card(shell, [at(*vertices[i]) for i in ids], normal)
        # Apply the same taper to every point, including the internal fillets.
        depth=.52; contractions=(0., .12, .34, .48); depths=(0., .07, depth-.08, depth)
        field_rings=[]; field_ns=[]
        for contraction, d in zip(contractions, depths):
            xy, ns=rounded_rect(field_width-2*contraction, field_height-2*contraction, 1.2-contraction)
            xy[:, 1]+=middle
            field_rings.append([at(x,z,d) for x,z in xy]); field_ns.append(ns)
        for j in range(3):
            for i in range(len(field)):
                k=(i+1)%len(field)
                def n(row,col):
                    slope=0 if row in (0,3) else .8
                    return P.unit(normal-(right*field_ns[row][col][0]+Z*field_ns[row][col][1])*slope)
                card(shell,(field_rings[j][i],field_rings[j][k],field_rings[j+1][k],field_rings[j+1][i]),normal,
                     normals=(n(j,i),n(j,k),n(j+1,k),n(j+1,i)))
        inner,_=rounded_rect(field_width-.96,field_height-.96,.72);inner[:,1]+=middle
        handle_z=H*.385; handle_width=min(9.8,half_width*.77)
        pocket_width=handle_width+3.2; pocket_height=5.1
        pocket,_=rounded_rect(pocket_width,pocket_height,1.08);pocket[:,1]+=handle_z
        flutes=[]
        for sign in ((-1,1) if abs(float(np.dot(normal,Y)))>.5 else ()):
            flute,_=rounded_rect(2.65,field_height-2.1,.65)
            flute[:,0]+=sign*(field_width*.385);flute[:,1]+=middle
            flutes.append(flute)
        holes=((*((pocket,) if handle else ()),*flutes))
        vertices,triangles=triangulate(inner, holes)
        for ids in triangles: card(shell,[at(*vertices[i],depth) for i in ids],normal)
        for flute in flutes:
            # The closed reinforcement channels sit in the recessed field.
            centre=flute.mean(axis=0);contours=[]
            for shrink,d in ((0.,depth),(.10,depth+.07),(.26,depth+.34),(.36,depth+.39)):
                xy,_=rounded_rect(2.65-2*shrink,field_height-2.1-2*shrink,max(.2,.65-shrink))
                contours.append([at(x+centre[0],z+centre[1],d) for x,z in xy])
            for j in range(3):
                for i in range(len(flute)):
                    k=(i+1)%len(flute)
                    card(shell,(contours[j][i],contours[j][k],contours[j+1][k],contours[j+1][i]),normal)
            card(shell,contours[-1],normal)
        if handle:
            # A genuinely recessed well, with a replaceable folding D handle.
            handle_rings=[];handle_ns=[]
            for contraction,d in ((0,depth),(.13,depth+.12),(.35,depth+.78),(.48,depth+.87)):
                xy,ns=rounded_rect(pocket_width-2*contraction,pocket_height-2*contraction,1.08-contraction)
                handle_rings.append([at(x,z+handle_z,d) for x,z in xy]);handle_ns.append(ns)
            for j in range(3):
                for i in range(len(pocket)):
                    k=(i+1)%len(pocket)
                    outward=normal-right*handle_ns[j][i][0]-Z*handle_ns[j][i][1]
                    card(rim,(handle_rings[j][i],handle_rings[j][k],handle_rings[j+1][k],handle_rings[j+1][i]),outward)
            card(rubber,handle_rings[-1],normal)
            mount=at(0,handle_z,depth+.65); hw=handle_width/2
            for sign in (-1,1):
                boss=mount+right*sign*hw+Z*.9
                box(boss,(.88,.30,1.18),steel,.13,axes=(right,normal,Z))
                P.rod(local,boss-right*.56,boss+right*.56,.225,alloy,10,caps=True)
            bar_y=normal*.40
            path=[mount-right*hw+Z*1.05,mount-right*hw-Z*.35+bar_y,
                  mount-right*(hw-.70)-Z*1.35+bar_y,mount+right*(hw-.70)-Z*1.35+bar_y,
                  mount+right*hw-Z*.35+bar_y,mount+right*hw+Z*1.05]
            P.tube(local,path,.255,steel,sides=8,bend_radius=.6)
            centre=mount-Z*1.35+bar_y
            length=handle_width-2.1
            P.lathe_axis(local,centre-right*length/2,right,
                         ((.32,0),(.44,.18),(.45,.50),(.39,length*.5),(.45,length-.50),(.44,length-.18),(.32,length)),
                         rubber,sides=10,cap=rubber)
        return at

    front=face(-Y,X,W/2,L/2)
    face(Y,-X,W/2,L/2,False)
    face(X,Y,L/2,W/2)
    face(-X,-Y,L/2,W/2)
    # Continuous wraparound corner guards grow out of the shell and blend back
    # into it at both ends, rather than ending as square bars on each wall.
    for corner in range(4):
        strips=[];directions=[]
        for z,strength in ((body_low+.05,0.),(body_low+.85,1.),(body_high-.90,1.),(body_high-.10,0.)):
            xy,ns=rounded_rect(L-2*inset(z),W-2*inset(z),radius)
            arc=xy[corner*5:corner*5+5];norm=ns[corner*5:corner*5+5]
            tang0=np.array((-norm[0][1],norm[0][0]));tang1=np.array((-norm[-1][1],norm[-1][0]))
            xy=np.vstack((arc[0]-tang0*1.65,arc,arc[-1]+tang1*1.65))
            norm=np.vstack((norm[0],norm,norm[-1]))
            mask=(0.,.8,1.,1.,1.,.8,0.)
            strips.append([np.array((*(p+n*.42*strength*m),z)) for p,n,m in zip(xy,norm,mask)])
            directions.append([P.unit((*n,0.)) for n in norm])
        for j in range(3):
            for i in range(6):
                card(rim,(strips[j][i],strips[j][i+1],strips[j+1][i+1],strips[j+1][i]),directions[j][i],
                     normals=(directions[j][i],directions[j][i+1],directions[j+1][i+1],directions[j+1][i]))
    # A broad rounded bottom band and narrow opaque gasket close the shell.
    loft(((.54,1.06),(.70,.91),(1.02,.77),(body_low,inset_low)),rim,bottom=True)
    card(shell,rings[-1],Z)
    loft(((seam-.28,.42),(seam+.14,.42)),gasket,bottom=True,top=True)
    loft(((seam+.10,.46),(seam+.27,.28),(seam+.65,.21)),shell,bottom=True)
    lid_low=seam+.65;lid_high=H-.95
    # Each lid wall has cut-in pockets aligned with the top channels. Its
    # reinforcement is continuous shell material with generous mould radii.
    for normal,right,half_depth,half_width,count in ((-Y,X,W/2,L/2,4),(Y,-X,W/2,L/2,4),
                                                    (X,Y,L/2,W/2,2),(-X,-Y,L/2,W/2,2)):
        span=half_width-radius-.21
        outer=np.array(((-span,lid_low),(span,lid_low),(span,lid_high),(-span,lid_high)))
        width=(L*.155) if count==4 else (W*.28)
        fractions=(-.315,-.105,.105,.315) if count==4 else (-.20,.20)
        full_width=L if count==4 else W
        pocket_height=lid_high-lid_low-.65;middle=(lid_low+lid_high)/2
        pockets=[]
        for fraction in fractions:
            xy,_=rounded_rect(width,pocket_height,.60);xy[:,0]+=full_width*fraction;xy[:,1]+=middle;pockets.append(xy)
        vertices,triangles=triangulate(outer,pockets)
        def at(x,z):return normal*(half_depth-.21)+right*x+Z*z
        for ids in triangles:card(shell,[at(*vertices[i]) for i in ids],normal)
        for fraction in fractions:
            formed_recess(at(full_width*fraction,middle),right,Z,normal,width,pocket_height,.60,.47,shell,shell)
    xy,ns=rounded_rect(L-.42,W-.42,radius)
    for corner in range(4):
        for i in range(corner*5,corner*5+4):
            a=np.array((*xy[i],lid_low));b=np.array((*xy[i+1],lid_low))
            card(shell,(a,b,b+Z*(lid_high-lid_low),a+Z*(lid_high-lid_low)),np.array((*ns[i],0.)),
                 normals=[np.array((*n,0.)) for n in (ns[i],ns[i+1],ns[i+1],ns[i])])
    lid=loft(((lid_high,.21),(H-.50,.30),(H,.56)),shell)

    # Four deep stacking channels are cut into the top cap. Remaining material
    # forms three substantial, connected ribs and a protective perimeter rim.
    cap=lid[-1][:,:2]; trays=[]
    for fraction in (-.315,-.105,.105,.315):
        xy,_=rounded_rect(L*.155,W-7.2,1.0);xy[:,0]+=L*fraction;trays.append(xy)
    vertices,triangles=triangulate(cap,trays)
    for ids in triangles: card(rim,[np.array((*vertices[i],H)) for i in ids],Z)
    for fraction in (-.315,-.105,.105,.315):
        formed_recess((L*fraction,0,H),X,Y,Z,L*.155,W-7.2,1.,.54,shell,shell)
    for sx in (-1,1):
        for sy in (-1,1):
            box((sx*(L/2-3.25),sy*(W/2-3.25),.35),(4.1,4.1,.70),rubber,.30)

    # Catches have separate mounting plates, formed levers, bail loops and pins.
    for sign in (-1,1):
        x=sign*L*.318;y=-W/2+.35
        box((x,y,seam-.25),(3.55,.42,5.25),rubber,.20)
        box((x,y-.26,seam-1.05),(2.72,.27,3.55),steel,.13)
        box((x,y-.28,seam+1.42),(2.62,.32,1.10),steel,.13)
        # The pressed lever's outline narrows at the pivot and curls at its lip.
        outline=np.array(((-.73,-1.8),(.73,-1.8),(1.02,-1.15),(1.02,.55),(.70,.92),(-.70,.92),(-1.02,.55),(-1.02,-1.15)))
        a=[np.array((x+u,y-.56,seam+z-.15)) for u,z in outline]
        b=[np.array((x+u*.90,y-.82,seam+z-.15)) for u,z in outline]
        for i in range(len(a)):
            k=(i+1)%len(a);card(steel,(a[i],a[k],b[k],b[i]),np.array((outline[i][0],-.35,outline[i][1])))
        card(steel,b,-Y)
        box((x,y-.84,seam-.87),(1.1,.045,.14),gasket,.035)
        P.rod(local,(x-1.18,y-.60,seam-1.55),(x+1.18,y-.60,seam-1.55),.205,alloy,10,caps=True)
        P.tube(local,[(x-.65,y-.65,seam+.27),(x-.65,y-.69,seam+1.82),
                      (x+.65,y-.69,seam+1.82),(x+.65,y-.65,seam+.27)],.105,alloy,sides=6,bend_radius=.20)
        for dx in (-.93,.93):
            screw((x+dx,y-.46,seam-2.35),-Y)
            screw((x+dx,y-.47,seam+1.42),-Y)
        # Back hinges use alternating knuckles round a continuous pin.
        for dz in (-1.,1.): box((x,W/2-.05,seam+dz),(3.3,.32,1.4),steel,.13)
        for a,b in ((-1.56,-.59),(-.49,.49),(.59,1.56)):
            P.rod(local,(x+a,W/2+.19,seam),(x+b,W/2+.19,seam),.31,steel,10,caps=True)
        P.rod(local,(x-1.66,W/2+.19,seam),(x+1.66,W/2+.19,seam),.13,alloy,8,caps=True)

    # Ribbed pressure valve with a distinct metal centre on the right end.
    valve=np.array((L/2-.30,0.,3.45))
    P.lathe_axis(local,valve,X,((.69,0),(.73,.12),(.73,.29),(.54,.38)),steel,16,cap=steel)
    P.lathe_axis(local,valve+X*.39,X,((.39,0),(.43,.04),(.43,.10),(.34,.15)),alloy,12,cap=alloy)
    for offset in (-.20,0,.20): box(valve+X*.56+Y*offset,(.035,.04,.43),gasket,.015)
    # UVs use the actual OBJ import's V convention. Each case gets one of 16 IDs.
    label_z=seam-2.85; label_y=-W/2+inset(label_z)+.48-.025
    hw=3.15;hh=.81;cell=seed%16;cx=cell%4;cy=cell//4
    u0=(cx*512+12)/2048;u1=(cx*512+500)/2048
    v0=1-(cy*256+244)/1024;v1=1-(cy*256+12)/1024
    card('vr_transport_label',[(-hw,label_y,label_z-hh),(hw,label_y,label_z-hh),
                               (hw,label_y,label_z+hh),(-hw,label_y,label_z+hh)],-Y,
         uv=((u0,v0),(u1,v0),(u1,v1),(u0,v1)))

    # Carry the exact authored transform and collision box into the map mesh.
    f=P.unit((along[0],along[1],0.));s=np.cross(Z,f);axes=np.array((f,s,Z));base=np.array((*c,z0))
    for mat,rows in local.polygons.items():
        for index,(points,normal) in enumerate(rows):
            normals=local.polygon_normals.get((mat,index))
            model.polygon(mat,[base+p@axes for p in points],normal=normal@axes,
                          normals=[n@axes for n in normals] if normals is not None else None,
                          uv=local.polygon_uvs.get((mat,index)))
    if surface: model.oriented_box(base+Z*(H/2),(f,s,Z),(L,W,H),{},surface)


def write_materials(directory):
    """Fine polymer grain and contact polish, without large camouflage mottles."""
    out=Path(directory);out.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(416033);n=1024
    def noise(sigma):
        a=gaussian_filter(rng.normal(size=(n,n)),sigma,mode='wrap')
        return a/max(a.std(),1e-9)
    grain=noise(.65); pores=noise(1.5); broad=noise(35); handling=noise(75)
    scratches=Image.new('L',(n,n));draw=ImageDraw.Draw(scratches)
    for _ in range(115):
        x,y=rng.uniform(0,n,2);length=rng.uniform(3,43);angle=rng.uniform(-.23,.23)
        draw.line((x,y,x+length*math.cos(angle),y+length*math.sin(angle)),fill=int(rng.integers(20,120)),width=1)
    scuffs=gaussian_filter(np.asarray(scratches,dtype=float)/255,.5)
    height=.0034*grain+.0011*pores-.0020*scuffs
    step=16/n
    dx=(np.roll(height,-1,1)-np.roll(height,1,1))/(2*step)
    dy=(np.roll(height,-1,0)-np.roll(height,1,0))/(2*step)
    normals=np.stack((-dx,dy,np.ones_like(dx)),axis=-1);normals/=np.linalg.norm(normals,axis=-1)[...,None]
    Image.fromarray(np.clip((normals*.5+.5)*255,0,255).astype('uint8')).save(out/'polymer_normal.png')
    for name,rough in (('polymer',.60),('rim',.47),('rubber',.78),('steel',.42)):
        a=rough+.025*grain+.025*handling-.22*scuffs
        Image.fromarray(np.clip(a*255,0,255).astype('uint8')).save(out/f'{name}_rough.png')
    Image.new('RGB',(16,16),(128,128,255)).save(out/'flat_normal.png')
    Image.new('L',(16,16),215).save(out/'flat_rough.png')
    for name,colour in (('rubber',(38,42,35)),('gasket',(15,18,13)),
                        ('steel',(94,101,91)),('alloy',(153,161,150))):
        Image.new('RGB',(64,64),colour).save(out/f'{name}_color.png')
    for name,colour in (('olive',(69.,77.,51.)),('black',(34.,38.,37.))):
        shade=1+.004*broad+.013*grain+.005*handling+.055*scuffs
        for suffix,multiplier in (('',1.),('_edge',1.065)):
            a=np.clip(shade[...,None]*np.array(colour)*multiplier,0,255).astype('uint8')
            Image.fromarray(a).save(out/f'{name+suffix}_color.png')
    label=Image.new('RGB',(2048,1024),(156,162,145));draw=ImageDraw.Draw(label)
    font=ImageFont.truetype('C:/Windows/Fonts/consolab.ttf',30)
    small=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',20)
    for i in range(16):
        x=(i%4)*512;y=(i//4)*256
        draw.rectangle((x+12,y+12,x+499,y+243),fill=(169,175,156),outline=(39,46,34),width=3)
        draw.text((x+27,y+22),'VERIDANT / EQUIPMENT',font=font,fill=(30,37,27))
        draw.text((x+28,y+70),'SEALED TRANSPORT / IP67',font=small,fill=(39,46,34))
        draw.text((x+28,y+104),f'VR-{420+i:03d}  /  INVENTORY {i+1:02d}',font=small,fill=(39,46,34))
        for bx in range(29,365,6):
            if rng.random()>.23: draw.rectangle((x+bx,y+147,x+bx+int(rng.integers(1,4)),y+210),fill=(36,43,31))
        draw.text((x+387,y+160),f'{i+1:02d}',font=font,fill=(36,43,31))
    label.save(out/'label_color.png')
    specs={name:(name,(1,1,1),0.,'polymer') for name in ('olive','black')}
    specs.update({name:(name,(1,1,1),0.,'rim') for name in ('olive_edge','black_edge')})
    specs.update({'rubber':('rubber',(1,1,1),0.,'rubber'),
                  'gasket':('gasket',(1,1,1),0.,'rubber'),
                  'steel':('steel',(1,1,1),.12,'steel'),
                  'alloy':('alloy',(1,1,1),.78,'steel'),
                  'label':('label',(1,1,1),0.,'polymer')})
    for name,(texture,tint,metal,rough) in specs.items():
        colour=f'{PREFIX}/{texture}_color.png' if texture else 'materials/default/default_color.tga'
        normal='flat_normal' if name in ('label','alloy','gasket') else 'polymer_normal'
        text=('// Tools/veridant_case_detail.py\n"Layer0"\n{\n'
              '    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n'
              f'    g_flRoughnessScaleFactor "1"\n    g_flMetalness "{metal}"\n'
              f'    TextureColor "{colour}"\n    TextureNormal "{PREFIX}/{normal}.png"\n'
              f'    TextureRoughness "{PREFIX}/{rough}_rough.png"\n'
              '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n'
              f'    g_vColorTint "[{tint[0]} {tint[1]} {tint[2]} 1]"\n    g_flModelTintAmount "1.0"\n}}\n')
        (out/f'{name}.vmat').write_text(text)
