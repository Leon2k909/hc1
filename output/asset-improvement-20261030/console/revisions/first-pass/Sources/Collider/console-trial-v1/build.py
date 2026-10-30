"""Isolated proposal for the actual east Collider control console. Never installs it."""
import os
for name in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[name]='1'
import psutil
proc=psutil.Process();proc.nice(psutil.IDLE_PRIORITY_CLASS)
proc.cpu_affinity(proc.cpu_affinity()[-2:])
from pathlib import Path
from collections import Counter
import argparse
import hashlib
import json
import math
import sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import scipy.ndimage as ndi

ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import collider_map as M
import collider_operators as O
import collider_services as S
from belltower_furniture import face,bevel_box
OUT=ROOT/'output/asset-improvement-20261030/console'
RESOURCE='models/props/collider/console-trial-v1';MAT='materials/collider/console-trial-v1'
DEST=ROOT/'Assets'/RESOURCE;MD=ROOT/'Assets'/MAT
ORIGIN=np.array((1755.,-55.,256.));ROT=np.array(((0.,-1.,0.),(1.,0.,0.),(0.,0.,1.)))
UP=np.array((0.,0.,1.));FRONT=np.array((0.,-1.,0.));AXES=np.eye(3)
ANGLE=math.atan2(18,61);C=math.cos(ANGLE);SN=math.sin(ANGLE)
DECK_AXES=np.array(((1.,0.,0.),(0.,C,SN),(0.,-SN,C)))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def key(p,points):
    return p,tuple(sorted(tuple(round(float(v),3) for v in pt) for pt in points))


def baseline():
    raw=K.Model();M._legacy_control_desk(raw,1,-55.,256.,True,render_chair=False)
    expected=Counter(key(p,[ps[0],ps[i],ps[i+1]]) for p,polys in raw.polygons.items()
                     for ps,n in polys for i in range(1,len(ps)-1))
    remaining=expected.copy();before=K.Model();vs=[];uv=[];ns=[];paint=''
    source=ROOT/'Assets/models/maps/collider/collider_structure.obj'
    for line in source.read_text().splitlines():
        if line.startswith('v '):
            a,z,n=map(float,line.split()[1:]);vs.append(np.array((-a,n,z)))
        elif line.startswith('vt '):uv.append(tuple(map(float,line.split()[1:])))
        elif line.startswith('vn '):
            a,z,n=map(float,line.split()[1:]);ns.append(np.array((-a,n,z)))
        elif line.startswith('usemtl '):paint=line[7:]
        elif line.startswith('f ') and paint in raw.polygons:
            ids=[[int(v)-1 for v in t.split('/')] for t in line.split()[1:]]
            points=[vs[v] for v,t,n in ids];signature=key(paint,points)
            if remaining[signature]:
                remaining[signature]-=1
                before.polygon(paint,[ROT@(p-ORIGIN) for p in points],
                               uv=[uv[t] for v,t,n in ids],normals=[ROT@ns[n] for v,t,n in ids])
    assert not +remaining,('Saved baseline missing',sum((+remaining).values()))
    # Only the existing desk clip: the approved chair is a different asset.
    before.box((-56,25,6),(56,115,38),None,'metal')
    M.configure(before)
    return before,{'source':source.relative_to(ROOT).as_posix(),'sourceSHA256':sha(source),
        'planOrigin':ORIGIN.tolist(),'planToCanonicalRotation':ROT.tolist(),
        'station':{'side':1,'north':-55,'floorHeight':256},
        'exactMatchedTriangles':sum(expected.values()),'copiedSavedGeometryUVsNormals':True}


def block(m,at,size,paint='cp_body',radius=.5,bevel=.12,axes=AXES):
    O.round_block(m,np.array(at,float),size,paint,radius,bevel,axes=axes,segments=3)


def screw(m,at,normal=FRONT,r=.30):
    p=np.asarray(at,float);n=np.asarray(normal,float)
    O.turned(m,p,n,[(r*.8,0),(r,.035),(r*.83,.13)],'cp_metal',12)
    # Actual slotted head; dark, shallow and narrower than the head.
    x=np.array((1.,0.,0.))
    if abs(n@x)>.8:x=np.array((0.,1.,0.))
    y=K.normalise(np.cross(n,x));x=K.normalise(np.cross(y,n))
    m.oriented_box(p+n*.133,np.array((x,y,n)),(r*1.12,.045,.013),'cp_rubber')


LABELS=[('COLLIDER / RING CONTROL','OPERATOR CONSOLE   03'),
        ('ACCELERATOR SERVICES','AUTHORIZED PERSONNEL ONLY'),
        ('POWER DISTRIBUTION','ISOLATE BEFORE OPENING'),
        ('COOLING CIRCUIT','SUPPLY / RETURN'),
        ('EMERGENCY STOP','PUSH TO TRIP / TURN TO RESET'),
        ('LOCAL   REMOTE   LOCK','CONTROL AUTHORITY'),
        ('VACUUM   FIELD   RF','SETPOINT / TRIM'),
        ('SERVICE ACCESS','REV C   /   UNIT CR-03'),
        ('STANDBY  /  READY','INTERLOCK STATUS'),
        ('CONTROL SYSTEMS','SERIAL 0317-0426')]


def label(m,index,at,w,h,axes=None):
    # Label plane axes are right and up; default is a vertical front panel.
    a,b=(np.array((1,0,0)),UP) if axes is None else axes
    p=np.asarray(at,float);normal=K.normalise(np.cross(a,b))
    col,row=index%2,index//2;rows=5
    uv=[(col*.5,(rows-row-1)/rows),((col+1)*.5,(rows-row-1)/rows),
        ((col+1)*.5,(rows-row)/rows),(col*.5,(rows-row)/rows)]
    face(m,'cp_label',[p-a*w/2-b*h/2,p+a*w/2-b*h/2,p+a*w/2+b*h/2,p-a*w/2+b*h/2],normal,uv=uv)


def deckpoint(x,y,lift=0):return np.array((x,y,40+y*18/61))+np.array((0,-SN,C))*lift


def candidate():
    m=K.Model()
    # Existing footprint and desk clip retained. Split service fronts expose seams,
    # folded returns and toe clearance instead of changing the room or the chair.
    block(m,(0,70,8),(109,86,4),'cp_rubber',1.,.3)
    block(m,(0,70,22.7),(112,90,31.5),'cp_body',1.0,.35)
    for x in (-55.7,55.7):
        block(m,(x,70,23),(1.4,89,31),'cp_edge',.4,.12)
        for y in (32,107):
            for z in (12,34):screw(m,(x+np.sign(x)*.73,y,z),(np.sign(x),0,0),.28)
    # Three separate front doors: genuine inset vent cavities in the lower band.
    for i,x in enumerate((-37.,0.,37.)):
        block(m,(x,24.94,23),(35.4,.45,28.0),'cp_rubber',.5,.08)
        block(m,(x,24.42,28.3),(34.6,.65,15.4),'cp_panel',.55,.12)
        block(m,(x,24.42,10.7),(34.6,.65,3.5),'cp_panel',.4,.1)
        for xx in (x-16.5,x+16.5):block(m,(xx,24.42,16.0),(1.6,.65,7.6),'cp_body',.25,.1)
        block(m,(x,26.,16.1),(31,.25,7.5),'cp_rubber',.35,.06)
        for z in np.arange(12.8,20.,1.15):
            block(m,(x,24.30,z),(31.4,1.,.62),'cp_edge',.15,.08)
        for xx in (x-14.8,x+14.8):
            for z in (10.6,34.):screw(m,(xx,24.05,z),FRONT,.26)
        # Real pulls attached by standoffs; locks with inset slots.
        for xx in (x-3,x+3):O.tube(m,(xx,24.0,30.5),(xx,22.7,30.5),.22,'cp_metal',12)
        O.tube(m,(x-3,22.7,30.5),(x+3,22.7,30.5),.25,'cp_metal',16)
        screw(m,(x+12.1,24.,28.8),FRONT,.48)
        label(m,(2,3,7)[i],(x,24.065,24.4),23,2.5)
    # Rubber levelling shoes align with the old plinth/clip envelope.
    for x in (-46,46):
        for y in (34,106):
            O.turned(m,(x,y,6),UP,[(2.5,0),(2.5,.7),(1.3,1.0),(1.3,2.5)],'cp_rubber',20)
    # Sloped deck has closed thickness, rounded corners and a separate front grip.
    length=math.hypot(61,18)
    block(m,(0,30.5,48.9),(118,length,1.65),'cp_deck',1.8,.24,DECK_AXES)
    block(m,(0,.6,39.9),(114,2.2,2.4),'cp_rubber',.8,.28,DECK_AXES)
    block(m,(0,89,39),(118,59,1.65),'cp_body',1.6,.24)
    for x in (-57.5,57.5):
        # Rolled side trim and gussets meet both ends of the keyboard deck.
        from belltower_furniture import beam
        beam(m,(x,1,40),(x,60.2,57.5),(1.25,1.8),'cp_edge',.18)
        crosssection=[(25,39),(60,39),(60,57.6),(25,47.3)]
        left=[np.array((x-.5,y,z)) for y,z in crosssection]
        right=[np.array((x+.5,y,z)) for y,z in crosssection]
        face(m,'cp_body',left,(-1,0,0));face(m,'cp_body',right,(1,0,0))
        for i in range(4):
            j=(i+1)%4;pts=[left[i],left[j],right[j],right[i]]
            normal=np.cross(pts[1]-pts[0],pts[2]-pts[0])
            face(m,'cp_body',pts,normal)
    for x in (-53.,53.):
        for y in (5.,55.):screw(m,deckpoint(x,y,1.02),(0,-SN,C),.28)
    # Real, correctly sized keyboard/mouse. Reuse the authored key legend atlas.
    kb=K.Model();O.keyboard(kb,1);pivot=np.array((-1.8,13.,34.5))
    loc=deckpoint(-5,22,1.28)
    kb=O.transform(kb,loc-pivot@DECK_AXES,DECK_AXES)
    remap={'op_shell':'cp_caps','op_paint':'cp_body','co_rubber':'cp_rubber','op_keys':'cp_keys'}
    for paint,polys in kb.polygons.items():
        for i,(ps,n) in enumerate(polys):
            m.polygon(remap[paint],ps,n,uv=kb.polygon_uvs.get((paint,i)),normals=kb.polygon_normals.get((paint,i)))
    # Recessed control panels sit just above the deck, not floating labels.
    for x in (-36.,35.):
        block(m,deckpoint(x,24,1.25),(23.,25.,1.05),'cp_rubber',1.1,.15,DECK_AXES)
        block(m,deckpoint(x,24,1.73),(22.1,24.1,.25),'cp_body',.9,.07,DECK_AXES)
        for xx in (-9.5,9.5):
            for yy in (-10.5,10.5):screw(m,deckpoint(x+xx,24+yy,1.94),(0,-SN,C),.18)
    for x in (-43.,-36.,-29.):
        p=deckpoint(x,26,1.95);n=np.array((0,-SN,C))
        O.turned(m,p,n,[(1.12,0),(1.12,.25),(.82,.35),(.82,1.45),(.65,1.65)],'cp_caps',24)
        for a in np.linspace(0,math.tau,12,endpoint=False):
            # Fine physical grip ribs, not flat drawn circles.
            axis1=np.array((1,0,0));axis2=np.array((0,C,SN))
            off=(axis1*math.cos(a)+axis2*math.sin(a))*.83
            O.tube(m,p+off+n*.48,p+off+n*1.4,.075,'cp_edge',6)
        block(m,p+n*1.67,(.12,.65,.025),'cp_label_white',.03,.006,DECK_AXES)
    label(m,6,deckpoint(-36,18.5,1.91),18,2.2,(np.array((1,0,0)),np.array((0,C,SN))))
    n=np.array((0,-SN,C));p=deckpoint(35,27,1.95)
    O.turned(m,p,n,[(2.5,0),(2.5,.2),(2.1,.3)],'cp_amber',32)
    O.turned(m,p+n*.3,n,[(1.15,0),(1.15,.9),(1.9,1.0),(1.95,1.65),(1.8,1.9)],'cp_red',32)
    label(m,4,deckpoint(35,20.5,1.91),18,3.,(np.array((1,0,0)),np.array((0,C,SN))))
    for i,x in enumerate((27.,35.,43.)):
        p=deckpoint(x,32.5,1.95)
        O.turned(m,p,n,[(.72,0),(.72,.2),(.52,.3),(.52,.55)],'cp_metal',20)
        O.turned(m,p+n*.55,n,[(.47,0),(.47,.16),(.40,.25)],('cp_green','cp_amber','cp_red')[i],20)
    # Main display retains the old 100x48 active size, location and atlas quadrant.
    screen=K.Model();O.screen(screen,(0,63.,83.),100.,48.,1,1)
    for paint,polys in screen.polygons.items():
        name={'op_shell':'cp_body','op_paint':'cp_edge','op_alloy':'cp_metal','co_rubber':'cp_rubber','co_beam':'cp_green'}.get(paint,paint)
        for i,(ps,n) in enumerate(polys):
            m.polygon(name,ps,n,uv=screen.polygon_uvs.get((paint,i)),normals=screen.polygon_normals.get((paint,i)))
    # Rear steel stand, tilt joint, cable glands and slack service loops.
    block(m,(0,82,40.3),(27,31,1.5),'cp_edge',1.4,.25)
    block(m,(0,80,57),(4,6,34),'cp_body',.8,.24)
    O.turned(m,(-7,67.2,83),(1,0,0),[(3.5,0),(3.5,14)],'cp_edge',28)
    for x in (-7.1,7.1):screw(m,(x,67.2,83),(np.sign(x),0,0),1.25)
    from belltower_furniture import beam
    for x in (-3,3):beam(m,(x,80,66),(x,68,83),(2.,3.),'cp_body',.3)
    for x in (-44,44):
        for z in (63,103):screw(m,(x,66.57,z),(0,1,0),.30)
    for x in (-14.,14.):
        O.turned(m,(x,85.,40),UP,[(1.5,0),(1.5,.25),(1.15,.45)],'cp_rubber',24)
        S.pipe_run(m,[(x,65.3,71),(x,71,69),(x,77,56),(x,88,50),(x,85.,40.4)],.32,'cp_rubber',10,bend=5)
    # Separate rear cover seams and legible identification plates.
    for x in (-38.,38.):
        block(m,(x,115.45,23),(34.,.55,27.8),'cp_panel',.7,.12)
        for xx in (x-14,x+14):
            for z in (11,35):screw(m,(xx,115.76,z),(0,1,0),.28)
    block(m,(0,63.25,57.1),(50,.6,2.8),'cp_body',.4,.09)
    label(m,0,(0,62.935,57.1),49,2.1)
    label(m,9,(0,62.935,107.42),25,.65)
    # Explicit physical UVs on the broad deck, avoiding a repeating tiled scuff map.
    for i,(ps,n) in enumerate(m.polygons['cp_deck']):
        m.polygon_uvs[('cp_deck',i)]=[((p[0]+59)/118,(p[1]*C+(p[2]-40)*SN)/length) for p in ps]
    m.box((-56,25,6),(56,115,38),None,'metal')
    existing=K.Model()
    for paint,polys in m.polygons.items():
        if not paint.startswith('cp_'):existing.polygons[paint]=polys
    M.configure(existing)
    m.material_overrides.update(existing.material_overrides);m.tile_overrides.update(existing.tile_overrides)
    for paint in m.polygons:
        if paint.startswith('cp_'):
            m.material_overrides[paint]=f'{MAT}/{paint}.vmat';m.tile_overrides[paint]=12.
    return m


def vmat(name,color,normal=None,rough=None,metal=0):
    return O.vmat(name,color,normal,rough,metal)


def materials():
    import ares_materials as AM
    MD.mkdir(parents=True,exist_ok=True);rng=np.random.default_rng(301026)
    n=1024;yy,xx=np.mgrid[:n,:n];x=xx/n;y=yy/n
    fine=rng.normal(0,1,(n,n));grain=ndi.gaussian_filter(fine,1.,mode='wrap')
    grain/=grain.std();broad=ndi.gaussian_filter(fine,36,mode='wrap');broad/=broad.std()
    medium=ndi.gaussian_filter(fine,9,mode='wrap');medium/=medium.std()
    for name,base,rough,metal in (
        ('cp_body',(57,67,68),.50,0),('cp_panel',(65,76,77),.53,0),
        ('cp_edge',(88,98,100),.46,.25),('cp_rubber',(24,26,27),.79,0),
        ('cp_caps',(36,40,42),.46,0),('cp_metal',(153,160,162),.32,.92),
        ('cp_red',(151,21,15),.43,0),('cp_amber',(190,124,22),.42,0),
        ('cp_green',(40,109,65),.40,0)):
        color=np.array(base)[None,None,:]*(1+.016*grain[...,None]+.025*broad[...,None])
        height=grain*(.00045 if name!='cp_metal' else .00010)
        r=np.clip(rough+.014*grain+.045*broad,.22,.92)
        if name in ('cp_body','cp_panel','cp_edge'):
            # Variable paint/coating, a few rubbed marks and fine localized nicks.
            pits=(grain>2.0)&(medium>.4);color[pits]*=.68;height[pits]-=.0016;r[pits]+=.12
        if name=='cp_metal':
            scratches=(np.sin(x*math.tau*430)+np.sin(x*math.tau*293))*.5
            color*=1+.025*scratches[...,None];height+=scratches*.00007
        for suffix,data in (('color',color),('rough',r*255)):
            Image.fromarray(np.clip(data,0,255).astype('uint8')).save(MD/(name+'_'+suffix+'.png'))
        normal=AM.normals(height,(n/12,n/12));AM.BX.save_normal(MD/(name+'_normal.png'),normal)
        path=f'{MAT}/{name}';(MD/(name+'.vmat')).write_text(vmat(name,path+'_color.png',path+'_normal.png',path+'_rough.png',metal))
    # Unique work surface: wear follows the front lip, hand rests and controls.
    scratch=Image.new('L',(n,n));d=ImageDraw.Draw(scratch)
    for _ in range(260):
        a,b=rng.uniform(0,n),rng.uniform(0,n);length=rng.uniform(3,45)
        d.line((a,b,a+length,b+rng.normal(0,3)),fill=int(rng.uniform(40,155)),width=1)
    sc=np.asarray(scratch)/255
    wear=np.exp(-((y-.06)/.075)**2)*(.25+.15*medium)
    for cx,cy,rx,ry in ((.44,.32,.16,.12),(.18,.42,.10,.20),(.80,.42,.10,.20)):
        wear+=.22*np.exp(-(((x-cx)/rx)**2+((y-cy)/ry)**2))
    wear=np.clip(wear,0,1)
    edges=np.minimum.reduce((x,1-x,y,1-y));grime=np.exp(-np.maximum(0,edges)/.018)*(.1+.06*broad)
    color=np.array((64.,70.,69.))[None,None,:]*(1+.028*broad[...,None]+.009*grain[...,None])
    color*=1-grime[...,None];color+=sc[...,None]*17+wear[...,None]*5
    r=np.clip(.58+.04*broad-.14*wear+.06*grime+.05*sc,.30,.83)
    height=grain*.00042-sc*.0018
    Image.fromarray(np.clip(color,0,255).astype('uint8')).save(MD/'cp_deck_color.png')
    AM.BX.save_grey(MD/'cp_deck_rough.png',r)
    AM.BX.save_normal(MD/'cp_deck_normal.png',AM.normals(height,(n/118,n/math.hypot(61,18))))
    (MD/'cp_deck.vmat').write_text(vmat('cp_deck',f'{MAT}/cp_deck_color.png',f'{MAT}/cp_deck_normal.png',f'{MAT}/cp_deck_rough.png'))
    # Reuse the existing authored keyboard legend layout in this private material.
    atlas=Image.new('RGB',(1024,128*O.GLYPH_ROWS),(36,40,42));d=ImageDraw.Draw(atlas)
    for i,word in enumerate(O.GLYPHS):
        font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',40 if len(word)==1 else 19 if len(word)>3 else 25)
        d.text(((i%8)*128+64,(i//8)*128+64),word if word!='SPACE' else '',font=font,anchor='mm',fill=(166,175,175))
    atlas.save(MD/'cp_keys_color.png');(MD/'cp_keys.vmat').write_text(vmat('cp_keys',f'{MAT}/cp_keys_color.png',rough='[0.50 0.50 0.50 0]'))
    atlas=Image.new('RGB',(2048,1024),(177,178,165));d=ImageDraw.Draw(atlas)
    f1=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',45);f2=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',28)
    for i,(a,b) in enumerate(LABELS):
        cx=(i%2)*1024+512;cy=(i//2)*204.8+102.4
        d.rectangle((cx-492,cy-84,cx+492,cy+84),outline=(70,76,74),width=2)
        d.text((cx,cy-24),a,font=f1,anchor='mm',fill=(31,42,41))
        d.text((cx,cy+34),b,font=f2,anchor='mm',fill=(59,65,59))
    atlas.save(MD/'cp_labels_color.png');(MD/'cp_label.vmat').write_text(vmat('cp_label',f'{MAT}/cp_labels_color.png',rough='[0.66 0.66 0.66 0]'))
    (MD/'cp_label_white.vmat').write_text(vmat('cp_label_white','[0.65 0.66 0.59 0]',rough='[0.65 0.65 0.65 0]'))


def protected():
    paths=[ROOT/'Assets/models/maps/collider'/f'collider_{name}{ext}'
           for name in ('structure','detail','machine','glass') for ext in ('.obj','.mtl','.vmdl')]
    paths.append(ROOT/'Assets/scenes/maps/Collider/collider.scene')
    # Prevent inadvertently changing any of the previous approved private assets.
    for kind in ('models/props','materials'):
        paths.extend(p for p in (ROOT/'Assets'/kind/'collider').rglob('*')
                     if p.is_file() and 'trial-v1' in p.as_posix() and 'console-trial-v1' not in p.as_posix()
                     and p.suffix in ('.obj','.mtl','.vmdl','.vmat','.png'))
    return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(paths))}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--refine',action='store_true');args=parser.parse_args()
    if DEST.exists():
        assert args.refine,'Proposal already exists; explicitly refine only owned files'
        old=json.loads((OUT/'manifest.json').read_text())
        for p,h in old['protectedSourceSHA256'].items():assert sha(ROOT/p)==h,p
    guards=protected();before,provenance=baseline();after=candidate()
    OUT.mkdir(parents=True,exist_ok=True);DEST.mkdir(parents=True,exist_ok=True);materials()
    variants={}
    for name,model in (('before',before),('after',after)):
        K.write_obj(DEST/(name+'.obj'),model,name);K.write_vmdl(DEST/(name+'.vmdl'),RESOURCE,name,model)
        variants[name]={'triangles':model.triangle_count(),'meshSHA256':sha(DEST/(name+'.obj'))}
    for p,h in guards.items():assert sha(ROOT/p)==h,p
    result={'status':'candidate-only-not-installed','userApproved':False,'editorUsed':False,
        'engineCompilation':'pending','baseline':provenance,'models':variants,
        'protectedSourceSHA256':guards,'originalRetained':True,'collisionBoxUnchanged':True,
        'workload':{'priority':'idle','affinityCPUs':proc.cpu_affinity(),'BLASThreads':1},
        'details':['closed rounded sloped deck','separate folded service panels and recessed open vents',
                   'proper keys and legends, mouse and mat','rotary controls and emergency stop',
                   'tilt stand and routed service loops','slotted fasteners and ID plates',
                   'physical paint grain, localized scratches, grime and hand-contact roughness'],
        'screenActiveSizeInches':[100,48],'originalScreenAtlasQuadrantPreserved':True}
    text=json.dumps(result,indent=2)+'\n';(OUT/'manifest.json').write_text(text);(Path(__file__).parent/'candidate.json').write_text(text)
    print(json.dumps({k:v for k,v in result.items() if k!='protectedSourceSHA256'}))


if __name__=='__main__':main()
