"""Isolated actual-source review of Collider's west cooling unit. No map installation."""
import os
for key in ('OPENBLAS_NUM_THREADS','OMP_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):os.environ[key]='1'
import psutil
proc=psutil.Process();proc.nice(psutil.IDLE_PRIORITY_CLASS);proc.cpu_affinity(proc.cpu_affinity()[-2:])
from pathlib import Path
from collections import Counter
import argparse,hashlib,json,math,sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont
import scipy.ndimage as ndi
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import collider_map as M
import collider_operators as O
import boxyard_map as B
import collider_services as S
from belltower_furniture import face,beam
OUT=ROOT/'output/asset-improvement-20261030/cooling-unit'
RESOURCE='models/props/collider/cooling-unit-trial-v1';MAT='materials/collider/cooling-unit-trial-v1'
DEST=ROOT/'Assets'/RESOURCE;MD=ROOT/'Assets'/MAT
ORIGIN=np.array((-1470.,1702.,20.));UP=np.array((0.,0.,1.));FRONT=np.array((0.,-1.,0.));AXES=np.eye(3)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def signature(p,ps):return p,tuple(sorted(tuple(round(float(v),3) for v in pt) for pt in ps))


def baseline():
    raw=K.Model();e=ORIGIN[0]
    M.box(raw,e-53,e+53,1710,1785,20,250,'co_steel',False)
    for zz in range(43,230,17):M.box(raw,e-44,e+44,1708,1710,zz,zz+7,'co_trim',False)
    M._legacy_monitor(raw,(e,1707,211),(0,-1),56,28,2)
    expected=Counter(signature(p,[ps[0],ps[i],ps[i+1]]) for p,polys in raw.polygons.items()
                     for ps,n in polys for i in range(1,len(ps)-1))
    remaining=expected.copy();before=K.Model();vs=[];uv=[];ns=[];paint=''
    source=ROOT/'Assets/models/maps/collider/collider_machine.obj'
    with source.open() as f:
        for line in f:
            if line.startswith('v '):
                a,z,n=map(float,line.split()[1:]);vs.append(np.array((-a,n,z)))
            elif line.startswith('vt '):uv.append(tuple(map(float,line.split()[1:])))
            elif line.startswith('vn '):
                a,z,n=map(float,line.split()[1:]);ns.append(np.array((-a,n,z)))
            elif line.startswith('usemtl '):paint=line.split()[1]
            elif line.startswith('f ') and paint in raw.polygons:
                ids=[[int(v)-1 for v in t.split('/')] for t in line.split()[1:]]
                pts=[vs[v] for v,t,n in ids];key=signature(paint,pts)
                if remaining[key]:
                    remaining[key]-=1;before.polygon(paint,[p-ORIGIN for p in pts],
                        uv=[uv[t] for v,t,n in ids],normals=[ns[n] for v,t,n in ids])
    assert not +remaining and before.triangle_count()==170
    M.configure(before)
    return before,{'source':source.relative_to(ROOT).as_posix(),'sourceSHA256':sha(source),
        'planOrigin':ORIGIN.tolist(),'exactMatchedTriangles':170,'copiedSavedGeometryUVsNormals':True}


def block(m,p,size,paint='cu_body',radius=.5,bevel=.12,axes=AXES):
    O.round_block(m,np.asarray(p,float),size,paint,radius,bevel,axes=axes,segments=3)


def turned(m,p,axis,profile,paint='cu_metal',sides=24):O.turned(m,p,axis,profile,paint,sides)
def tube(m,a,b,r,paint='cu_metal',sides=12):O.tube(m,a,b,r,paint,sides)


def screw(m,p,normal=FRONT,r=.38):
    p=np.asarray(p,float);n=np.asarray(normal,float)
    turned(m,p,n,[(r*.8,0),(r,.05),(r*.84,.18)],'cu_metal',12)
    a=np.array((1.,0.,0.))
    if abs(a@n)>.8:a=np.array((0.,1.,0.))
    b=K.normalise(np.cross(n,a));a=K.normalise(np.cross(b,n))
    m.oriented_box(p+n*.183,(a,b,n),(r*1.05,.075,.022),'cu_dark')


def ring(m,at,axis,inside,outside,depth,paint='cu_edge',sides=48):
    B.lathe(m,at,axis,[(inside,-depth/2),(outside,-depth/2),(outside,depth/2),
                      (inside,depth/2),(inside,-depth/2)],paint,sides=sides)


def torus(m,c,r,t,paint='cu_guard',major=48,minor=6):
    c=np.asarray(c,float)
    def point(i,j):
        a=math.tau*i/major;b=math.tau*j/minor
        normal=np.array((math.cos(a)*math.cos(b),-math.sin(b),math.sin(a)*math.cos(b)))
        p=c+np.array((r*math.cos(a),0,r*math.sin(a)))+t*normal
        return p,normal
    for i in range(major):
        for j in range(minor):
            values=[point(i,j),point(i+1,j),point(i+1,j+1),point(i,j+1)]
            face(m,paint,[p for p,n in values],sum(n for p,n in values),normals=[n for p,n in values])


def fan_panel(m,x,z,index):
    c=np.array((x,6.8,z));sides=48
    # Four-sided cartridge front has a real circular hole, with closed cut edge.
    inner=[];outer=[]
    for i in range(sides):
        a=math.tau*i/sides;u,v=math.cos(a),math.sin(a);r=23.6/max(abs(u),abs(v))
        inner.append(c+np.array((u*20.6,0,v*20.6)))
        outer.append(c+np.array((u*r,0,v*r)))
    for i in range(sides):
        j=(i+1)%sides
        face(m,'cu_body',[inner[i],inner[j],outer[j],outer[i]],FRONT)
        face(m,'cu_body',[p+(0,.8,0) for p in (inner[i],inner[j],outer[j],outer[i])],-FRONT)
        face(m,'cu_edge',[inner[i],inner[j],inner[j]+(0,.8,0),inner[i]+(0,.8,0)],
             -K.normalise(inner[i]+inner[j]-2*c))
        face(m,'cu_edge',[outer[i],outer[j],outer[j]+(0,.8,0),outer[i]+(0,.8,0)],K.normalise(outer[i]+outer[j]-2*c))
    ring(m,c+(0,.2,0),FRONT,19.65,21.15,1.5,'cu_edge')
    ring(m,c+(0,5.,0),FRONT,19.25,19.75,9.5,'cu_dark')
    # Deep motor and spokes are physically behind the blade/guard planes.
    turned(m,c+(0,14,0),FRONT,[(4.9,0),(4.9,7),(4.2,8.2)],'cu_dark',32)
    for a in np.linspace(0,math.tau,4,endpoint=False):
        tube(m,c+(0,13,0),c+np.array((18*math.cos(a),13,18*math.sin(a))),.6,'cu_edge',10)
    phase=index*.41
    for k in range(5):
        def surface(r,t):
            a=phase+k*math.tau/5+.78*t-.20*(r-4.5)/14.5
            return c+np.array((r*math.cos(a),7.+(t-.5)*4.4,r*math.sin(a)))
        def normal(r,t):
            return K.normalise(np.cross(surface(r+.001,t)-surface(r-.001,t),surface(r,t+.001)-surface(r,t-.001)))
        for i in range(8):
            r0=4.5+14.2*i/8;r1=4.5+14.2*(i+1)/8
            for j in range(4):
                t0=j/4;t1=(j+1)/4
                values=[(r0,t0),(r1,t0),(r1,t1),(r0,t1)]
                ps=[surface(r,t) for r,t in values];ns=[normal(r,t) for r,t in values]
                face(m,'cu_blade',ps,sum(ns),normals=ns)
                face(m,'cu_blade',[p+(0,.18,0) for p in ps],-sum(ns),normals=[-n for n in ns])
        # Closed root/tip/leading/trailing edges on each curved sheet-metal blade.
        edges=[]
        for t in (0.,1.):
            edges.extend(((4.5+14.2*i/8,t),(4.5+14.2*(i+1)/8,t),-1 if t==0 else 1) for i in range(8))
        for r in (4.5,18.7):edges.extend(((r,j/4),(r,(j+1)/4),1 if r==4.5 else -1) for j in range(4))
        for start,end,sign in edges:
            a=surface(*start);b=surface(*end);d=np.array((0,.18,0))
            pts=[a,b,b+d,a+d];face(m,'cu_blade',pts,sign*np.cross(b-a,d))
    turned(m,c+(0,5.3,0),FRONT,[(4.5,0),(4.5,1.1),(3.8,1.7)],'cu_edge',32)
    screw(m,c+(0,3.5,0),FRONT,.75)
    # A bowed wire guard, separate from the fan, catches highlights and casts shadows.
    for r in (5.3,11.0,18.0):torus(m,c+(0,-1.25,0),r,.18)
    for a in np.linspace(0,math.tau,8,endpoint=False):
        start=c+np.array((math.cos(a)*4.8,-1.25,math.sin(a)*4.8))
        end=c+np.array((math.cos(a)*20.5,-.65,math.sin(a)*20.5))
        tube(m,start,end,.17,'cu_guard',8)
    for dx in (-21.8,21.8):
        for dz in (-21.8,21.8):screw(m,c+(dx,-.2,dz),FRONT,.32)


LABELS=[('COLLIDER  /  COOLANT SERVICES','CCU-07   /   SECONDARY LOOP'),
        ('WARNING  /  AUTOMATIC START','ISOLATE ELECTRICAL SUPPLY BEFORE SERVICE'),
        ('HEAT EXCHANGER','FLOW  120 m3/h   /   400 V  3~  50 Hz'),
        ('SERVICE PANEL','REV C  /  UNIT 07  /  SERIAL 0317-0426'),
        ('SUPPLY   /   RETURN','NOMINAL  6.0 bar  /  18 C'),
        ('CAUTION  /  ROTATING EQUIPMENT','DO NOT REMOVE GUARDS WHILE RUNNING'),
        ('COOLANT CONTROL','STATUS / INTERLOCKS'),
        ('FLOW DIRECTION','AIR INTAKE  /  KEEP CLEAR')]


def label(m,index,p,w,h,right=np.array((1.,0.,0.)),up=UP):
    p=np.asarray(p,float);a=np.asarray(right);b=np.asarray(up);n=np.cross(a,b)
    col,row=index%2,index//2;u=col*.5;v=1-(row+1)/4
    face(m,'cu_label',[p-a*w/2-b*h/2,p+a*w/2-b*h/2,p+a*w/2+b*h/2,p-a*w/2+b*h/2],n,
         uv=[(u,v),(u+.5,v),(u+.5,v+.25),(u,v+.25)])


def dial(m,x,z):
    p=np.array((x,6.2,z))
    turned(m,p,FRONT,[(6.4,-.5),(6.4,.8),(6.0,1.3)],'cu_metal',48)
    turned(m,p+FRONT*1.31,FRONT,[(5.55,0),(5.55,.06)],'cu_dial',48)
    # Fine ticks/numerals use one nonrepeating dial face UV projection.
    for i,(ps,n) in enumerate(m.polygons['cu_dial']):
        if ('cu_dial',i) not in m.polygon_uvs:m.polygon_uvs[('cu_dial',i)]=[((a[0]-x)/11.1+.5,(a[2]-z)/11.1+.5) for a in ps]
    end=p+np.array((-2.9,-1.53,2.5))
    beam(m,p+(0,-1.53,0),end,(.18,.11),'cu_dark',.025)
    turned(m,p+FRONT*1.6,FRONT,[(.48,0),(.48,.13),(.34,.19)],'cu_metal',20)


def candidate():
    m=K.Model()
    # Grounded shoes support the original floating twenty-inch-high base.
    for x in (-43,43):
        for y in (17,73):
            block(m,(x,y,-18.8),(12,12,2.4),'cu_dark',1.1,.35)
            turned(m,(x,y,-17.6),UP,[(2.5,0),(2.5,2.0),(1.45,2.5),(1.45,17.6)],'cu_metal',24)
            for xx in (-3.8,3.8):screw(m,(x+xx,y,-17.5),UP,.55)
    block(m,(0,45.5,3),(106,75,6),'cu_edge',1.2,.4)
    block(m,(0,45.5,227.8),(106,75,4.4),'cu_body',1.4,.4)
    for x in (-50.8,50.8):
        for y in (10.5,80.5):block(m,(x,y,115),(4.4,4.4,224),'cu_edge',.65,.2)
    # Opaque rear service wall and separate upper control enclosure.
    for x in (-25.2,25.2):
        block(m,(x,81.8,116),(49.6,1.8,219),'cu_body',1.0,.25)
        for z in (12,110,220):
            for xx in (x-21,x+21):screw(m,(xx,82.75,z),(0,1,0),.36)
    block(m,(0,43.5,198.8),(100,69,56.8),'cu_body',1.1,.3)
    block(m,(0,7.5,191.4),(99,1.1,44.2),'cu_dark',.8,.2)
    block(m,(0,6.75,191.4),(97.6,.8,42.8),'cu_panel',.7,.2)
    # Six independently mounted fan cartridges form the front heat-rejection bank.
    index=0
    for z in (43.,93.,143.):
        for x in (-24.,24.):fan_panel(m,x,z,index);index+=1
    for z in (18.,68.,118.,168.):block(m,(0,10.5,z),(99,5.,2.2),'cu_edge',.45,.15)
    for x in (-48.7,0.,48.7):block(m,(x,10,93),(1.8,5.,148),'cu_edge',.35,.12)
    # Heat-exchanger fins are actual geometry; header pipes connect top and bottom.
    for sign in (-1,1):
        side_axes=np.array(((0.,sign,0.),(0.,0.,1.),(sign,0.,0.)))
        block(m,(sign*51.9,46.,93.),(63.,152.,.6),'cu_dark',1.,.15,side_axes)
        for y in (17.,75.):
            tube(m,(sign*50.5,y,18),(sign*50.5,y,167),1.55,'cu_metal',20)
        for z in np.arange(23.,166.,2.1):
            # A folded fin section has depth and a physically visible leading edge.
            m.oriented_box((sign*52.2,46,z),side_axes,(56.,.28,1.1),'cu_fin')
        for z in (17.,168.):
            block(m,(sign*52.1,46,z),(63.,3.,1.5),'cu_edge',.6,.2,side_axes)
        # Upper access cover with hinges, pull and attached fasteners.
        block(m,(sign*52.35,46,196),(60,42,.75),'cu_panel',.9,.2,side_axes)
        for y in (20,72):
            for z in (179,213):screw(m,(sign*52.76,y,z),(sign,0,0),.35)
        label(m,3,(sign*52.745,46,202),36,4.,right=np.array((0.,sign,0.)))
    # High loop piping, insulation bands and two coolant connections stay in the envelope.
    for x in (-33.,33.):
        S.pipe_run(m,[(x,65,9),(x,65,24),(x,58,30),(x,58,159)],1.8,'cu_pipe',16,bend=8)
        for z in (12,30,150):ring(m,(x,58 if z>20 else 65,z),UP,1.8,3.2,1.25,'cu_metal',24)
        ring(m,(x,82.,25),(0,1,0),2.3,5.1,1.6,'cu_metal',32)
    # Preserve the existing display's size, location and active atlas quadrant.
    screen=K.Model();O.screen(screen,(0,5.,191.),56.,28.,2,1)
    mapping={'op_shell':'cu_dark','op_paint':'cu_edge','co_rubber':'cu_dark','co_beam':'cu_green','op_alloy':'cu_metal'}
    for paint,polys in screen.polygons.items():
        for i,(ps,n) in enumerate(polys):m.polygon(mapping.get(paint,paint),ps,n,
            uv=screen.polygon_uvs.get((paint,i)),normals=screen.polygon_normals.get((paint,i)))
    for x in (-39.,39.):dial(m,x,193.)
    for i,x in enumerate((-9.,0.,9.)):
        p=np.array((x,6.3,173.5));turned(m,p,FRONT,[(1.6,0),(1.6,.4),(1.15,.55),(1.15,.95)],'cu_edge',24)
        turned(m,p+FRONT*.96,FRONT,[(1.,0),(1.,.35),(.8,.48)],('cu_green','cu_amber','cu_red')[i],24)
    # Raised warning plates and a louvred top intake.
    block(m,(0,7.3,216.2),(96,1.3,10.5),'cu_dark',.65,.18)
    label(m,0,(0,6.63,217.2),90,6.2)
    block(m,(0,7.3,11),(91,1.4,7.2),'cu_body',.5,.14)
    label(m,1,(0,6.58,11),85,5.8)
    for x in (-24.,24.):
        block(m,(x,7.3,68),(27,2.1,2.3),'cu_amber',.25,.06)
        label(m,5,(x,6.23,68),26,1.8)
    for y in np.arange(15.,78.,5.0):block(m,(0,y,230.3),(95,1.6,.7),'cu_edge',.35,.12)
    # Special private materials retain true per-face physical scales.
    co=K.Model()
    for paint,polys in m.polygons.items():
        if not paint.startswith('cu_'):co.polygons[paint]=polys
    M.configure(co);m.material_overrides.update(co.material_overrides);m.tile_overrides.update(co.tile_overrides)
    for paint in m.polygons:
        if paint.startswith('cu_'):m.material_overrides[paint]=f'{MAT}/{paint}.vmat';m.tile_overrides[paint]=12.
    return m


def materials():
    import ares_materials as AM
    MD.mkdir(parents=True,exist_ok=True);n=1024;rng=np.random.default_rng(301030)
    y,x=np.mgrid[:n,:n]/n;fine=rng.normal(0,1,(n,n));grain=ndi.gaussian_filter(fine,.65,mode='wrap');grain/=grain.std()
    broad=ndi.gaussian_filter(fine,25,mode='wrap');broad/=broad.std()
    for name,base,rough,metal in (
        ('cu_body',(85,108,106),.52,0),('cu_panel',(102,120,116),.51,0),('cu_edge',(59,74,74),.46,.1),
        ('cu_dark',(24,29,30),.72,0),('cu_blade',(44,51,52),.44,.12),('cu_guard',(106,117,118),.32,.88),
        ('cu_metal',(158,163,161),.30,.92),('cu_fin',(116,125,123),.42,.82),('cu_pipe',(128,91,56),.38,.86),
        ('cu_green',(43,127,72),.36,0),('cu_amber',(190,123,25),.43,0),('cu_red',(146,24,18),.43,0)):
        color=np.array(base)[None,None,:]*(1+.014*grain[...,None]+.016*broad[...,None]);r=rough+.018*grain+.02*broad
        height=grain*(.0006 if metal<.5 else .00014)
        pits=(grain>1.8)&(broad>.4)
        if metal<.5:
            color[pits]*=.72;height[pits]-=.002;r[pits]+=.1
        else:
            brush=np.sin(y*math.tau*340)*.5+np.sin(y*math.tau*171)*.5
            color*=1+.022*brush[...,None];height+=brush*.00007
        Image.fromarray(np.clip(color,0,255).astype('uint8')).save(MD/(name+'_color.png'))
        AM.BX.save_grey(MD/(name+'_rough.png'),np.clip(r,.18,.94))
        AM.BX.save_normal(MD/(name+'_normal.png'),AM.normals(height,(n/12,n/12)))
        path=f'{MAT}/{name}';(MD/(name+'.vmat')).write_text(O.vmat(name,path+'_color.png',path+'_normal.png',path+'_rough.png',metal))
    # Clear dial graphics are authored, not a glowing blank disc.
    dial=Image.new('RGB',(1024,1024),(209,210,192));d=ImageDraw.Draw(dial)
    for i in range(61):
        a=math.radians(135+270*i/60);r0=385 if i%5==0 else 414
        d.line((512+math.cos(a)*r0,512+math.sin(a)*r0,512+math.cos(a)*458,512+math.sin(a)*458),fill=(34,43,40),width=8 if i%5==0 else 3)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',57)
    for i in range(7):
        a=math.radians(135+270*i/6);d.text((512+math.cos(a)*323,512+math.sin(a)*323),str(i*2),font=font,anchor='mm',fill=(43,51,46))
    d.text((512,600),'bar',font=font,anchor='mm',fill=(43,51,46))
    d.text((512,680),'CLASS 1.6',font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',28),anchor='mm',fill=(75,81,68))
    dial.save(MD/'dial_color.png');(MD/'cu_dial.vmat').write_text(O.vmat('cu_dial',f'{MAT}/dial_color.png',rough='[0.46 0.46 0.46 0]'))
    atlas=Image.new('RGB',(2048,1024),(189,190,171));d=ImageDraw.Draw(atlas)
    a=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',42);b=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',27)
    for i,(title,subtitle) in enumerate(LABELS):
        cx=(i%2)*1024+512;cy=(i//2)*256+128
        d.rectangle((cx-493,cy-105,cx+493,cy+105),outline=(70,78,66),width=3)
        d.text((cx,cy-30),title,font=a,anchor='mm',fill=(31,45,42));d.text((cx,cy+37),subtitle,font=b,anchor='mm',fill=(62,70,61))
    atlas.save(MD/'labels_color.png');(MD/'cu_label.vmat').write_text(O.vmat('cu_label',f'{MAT}/labels_color.png',rough='[0.65 0.65 0.65 0]'))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--refine',action='store_true');parser.add_argument('--geometry-only',action='store_true');args=parser.parse_args()
    if DEST.exists():
        assert args.refine
        previous=json.loads((OUT/'manifest.json').read_text())
        for path,h in previous['protectedSourceSHA256'].items():assert sha(ROOT/path)==h,path
    # Reuse the approved console's broad source-guard inventory, evaluated afresh.
    import importlib.util
    spec=importlib.util.spec_from_file_location('console_build',ROOT/'Sources/Collider/console-trial-v1/build.py')
    C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C)
    guards=C.protected()
    guards.update({p.relative_to(ROOT).as_posix():sha(p) for directory in
        (ROOT/'Assets/models/props/collider/console-trial-v1',ROOT/'Assets/materials/collider/console-trial-v1')
        for p in directory.iterdir() if p.is_file() and p.suffix in ('.obj','.mtl','.vmdl','.vmat','.png')})
    # The guard helper includes all private trials; exclude only this owned candidate.
    guards={p:h for p,h in guards.items() if '/cooling-unit-trial-v1/' not in p}
    before,provenance=baseline();after=candidate()
    OUT.mkdir(parents=True,exist_ok=True);DEST.mkdir(parents=True,exist_ok=True)
    if not args.geometry_only:materials()
    variants={}
    for name,model in (('before',before),('after',after)):
        K.write_obj(DEST/(name+'.obj'),model,name);K.write_vmdl(DEST/(name+'.vmdl'),RESOURCE,name,model)
        variants[name]={'triangles':model.triangle_count(),'meshSHA256':sha(DEST/(name+'.obj'))}
    for path,h in guards.items():assert sha(ROOT/path)==h,path
    result={'status':'candidate-only-not-installed','userApproved':False,'editorUsed':False,'engineCompilation':'pending',
        'baseline':provenance,'models':variants,'protectedSourceSHA256':guards,'originalRetained':True,
        'collisionUnchanged':True,'collisionShapes':0,'sourceGroundPlaneLocalZ':-20,
        'newDetails':['six recessed fans with curved blades and separate wire guards',
            'real open fan cartridges and dark motor cavities','finned side heat exchangers and coolant headers',
            'slotted fasteners, service panels, physical gauges and identification plates',
            'grounded levelling supports','paint grain, nicks and brushed/tarnished metal'],
        'workload':{'priority':'idle','affinityCPUs':proc.cpu_affinity(),'BLASThreads':1}}
    for path in (OUT/'manifest.json',Path(__file__).parent/'candidate.json'):path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='protectedSourceSHA256'}))


if __name__=='__main__':main()
