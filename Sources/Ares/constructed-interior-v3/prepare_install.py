"""Stage the native-reviewed meshes and reproducible generator hooks."""
from pathlib import Path
import json,hashlib,re,ast
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;OUT=ROOT/'output/ares/constructed-interior-v3';STAGE=OUT/'install-stage'
manifest=json.loads((OUT/'manifest.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for p,h in manifest['guards'].items():assert sha(ROOT/p)==h,'Changed during review: '+p
def put(rel,text):
    p=STAGE/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='');return p
for model,primary in [('hall','models/maps/ares/pressure-doors-v2/hall_base.obj'),('reactor','models/maps/ares/ares_reactor.obj')]:
    doc=(OUT/f'stage/Assets/models/maps/ares/constructed-v3/ares_{model}_trial.vmdl').read_text()
    doc=doc.replace(f'models/maps/ares/constructed-v3/{model}.obj',primary,1)
    put(f'Assets/models/maps/ares/ares_{model}.vmdl',doc)
    put('Assets/'+primary,(OUT/f'stage/Assets/models/maps/ares/constructed-v3/{model}.obj').read_text().replace(f'mtllib {model}.mtl',f'mtllib {Path(primary).stem}.mtl'))
    put('Assets/'+str(Path(primary).with_suffix('.mtl')).replace('\\','/'),(OUT/f'stage/Assets/models/maps/ares/constructed-v3/{model}.mtl').read_text())
    # Existing secondary imports remain in their original order; the only new
    # filename is the separate skirt collision hull.
    original=(ROOT/f'Assets/models/maps/ares/ares_{model}.vmdl').read_text()
    old=re.findall(r'filename\s*=\s*"([^"]+)"',original);new=re.findall(r'filename\s*=\s*"([^"]+)"',doc)
    assert [p for p in new if not p.endswith('reactor_skirt_hulls.obj')]==old

g=(HERE/'geometry.py').read_text()
g=g.replace('def reactor(m):','def reactor(m,include_pumps=True):')
old='''    for e,n in ((270,270),(-270,270),(-270,-270),(270,-270)):
        pump(m,e,n,math.degrees(math.atan2(n,e))+90)'''
assert old in g;g=g.replace(old,'''    if include_pumps:
        for e,n in ((270,270),(-270,270),(-270,-270),(270,-270)):
            pump(m,e,n,math.degrees(math.atan2(n,e))+90)''')
g=g.replace('    return m\ndef box(','''    for legacy in ('steel','gunmetal','grating'):
        paint='ar_'+legacy
        if paint in m.polygons:m.material_overrides[paint]='materials/ares/surface-finish-v2/'+legacy+'.vmat'
    return m
def box(''',1)
collision=(HERE/'collision.py').read_text();tree=ast.parse(collision)
for node in tree.body:
    if isinstance(node,ast.FunctionDef) and node.name in ('supports','skirt'):
        text=ast.get_source_segment(collision,node).replace('G.X','X').replace('G.Y','Y').replace('G.Z','Z')
        if node.name=='supports':
            text=text.replace('def supports():\n    m=K.Model()','def support_collision(m):\n    start=len(m.boxes)').replace('len(m.boxes)==28','len(m.boxes)-start==28')
        g+='\n\n'+text+'\n'
g+='''
def retain_legacy_core(m):
    keep={'ar_plasma','ar_core','ar_signs','ar_copper','ar_led_warm','ar_led_amber','ar_screens'}
    for paint,polys in list(m.polygons.items()):
        selected=[];uvs={};normals={}
        for old,(points,normal) in enumerate(polys):
            if paint.startswith('ar_v3_') or paint in keep or min(p[2] for p in points)>=559:
                new=len(selected);selected.append((points,normal))
                if (paint,old) in m.polygon_uvs:uvs[(paint,new)]=m.polygon_uvs[(paint,old)]
                if (paint,old) in m.polygon_normals:normals[(paint,new)]=m.polygon_normals[(paint,old)]
        m.polygons[paint]=selected
        m.polygon_uvs={k:v for k,v in m.polygon_uvs.items() if k[0]!=paint};m.polygon_uvs.update(uvs)
        m.polygon_normals={k:v for k,v in m.polygon_normals.items() if k[0]!=paint};m.polygon_normals.update(normals)
'''
put('Tools/ares_constructed.py',g)

i=(ROOT/'Tools/ares_interior.py').read_text()
i=i.replace("FLOOR='ar_in_floor'","FLOOR='ar_in_floor'; WALL='ar_in_wall'")
i=i.replace('\ndef configure(m):',"\nMATERIALS.update({WALL:'materials/ares/surface-finish-v2/wall.vmat',FRAME:'materials/ares/surface-finish-v2/frame.vmat'})\n\ndef configure(m):")
i=i.replace('m.tile_overrides[paint]=96. if paint in (PANEL,FLOOR) else 48.','m.tile_overrides[paint]=192. if paint==WALL else 96. if paint in (PANEL,FLOOR) else 48.')
for a,b in [('.28,w-8,319),PANEL','.28,w-8,319),WALL'),('.58,n1-n0-2,146),PANEL','.58,n1-n0-2,146),WALL'),('(.6,96,120),PANEL','(.6,96,120),WALL')]:assert a in i;i=i.replace(a,b)
i+='''
# Constructed hall revision, reviewed as a separate native model before install.
def append_hall(m):
    import ares_constructed as C
    wall_panels(m)
    for e in (-900,-500,500,900):C.portal(m,e)
    for side in (-1,1):
        for n in (-600,-150,300):C.haunch(m,side,n)
    C.ceiling(m);C.galleries(m);C.floor(m);C.support_collision(m)
    configure(m);C.config(m)

def pump_unit(m,e,n,heading):
    import ares_constructed as C
    import ares_map as A
    A.Frame(e,n,heading).box(m,-36,36,-28,28,0,64,{'default':None},A.METAL)
    C.pump(m,e,n,heading);C.config(m)
'''
put('Tools/ares_interior.py',i)

a=(ROOT/'Tools/ares_map.py').read_text()
a=a.replace('for paint in list( model.polygons ):','for paint in list( model.polygons ):\n        if model.material_overrides.get(paint, "").startswith(("materials/ares/constructed-v3/", "materials/ares/surface-finish-v2/")):\n            continue',1)
old='''    for nn in ( -500.0, -100.0, 300.0, 700.0 ):
        m.box( ( -HALL_E, nn - 5, HALL_TOP - 14 ), ( HALL_E, nn + 5, HALL_TOP ), "ar_steel" )'''
assert old in a;a=a.replace(old,'    # Purlins and enclosed soffits are drawn by ares_constructed.ceiling().')
a=a.replace('def reactor( m, glass ):','def _legacy_reactor( m, glass ):',1)
pos=a.index('\n\n# ---------------------------------------------------------------------------------------------------------------------\n# The wings')
a=a[:pos]+'''

def reactor(m,glass):
    import ares_constructed as C
    _legacy_reactor(m,glass)
    C.retain_legacy_core(m);C.reactor(m,include_pumps=False)
    m.hulls.extend(C.skirt());C.config(m)
'''+a[pos:]
old='m.box( np.minimum( nlo, nhi ), np.maximum( nlo, nhi ), "ar_hazard", skip=end_faces + ( "-z", ) )'
assert old in a;a=a.replace(old,'''hall_flight=axis=="n" and sorted((abs(c0),abs(c1)))==[760,880] and s0==-470 and s1==-158 and z0==0 and z1==G
        nosing_paint="ar_v3_dark" if hall_flight and 1<=k<count-2 else "ar_hazard"
        m.box( np.minimum( nlo, nhi ), np.maximum( nlo, nhi ), nosing_paint, skip=end_faces + ( "-z", ) )''')
old='LightColor=color, Radius=float( radius ), Shadows=bool( shadows )'
assert old in a;a=a.replace(old,'''LightColor="3.57,3.57,3.57,1" if name.startswith("Hall ") else color,
                         Temperature=5000 if name.startswith("Hall ") else 6500,
                         Contribution="Diffuse, Transmissive" if name.startswith("Hall ") else "Diffuse, Specular, Transmissive",
                         Radius=float(radius), Shadows=bool(shadows)''')
put('Tools/ares_map.py',a)
for file in STAGE.glob('Tools/*.py'):compile(file.read_text(),str(file),'exec')

scene=json.loads((ROOT/'Assets/scenes/maps/Ares/ares.scene').read_text())
lights=next(g for g in scene['GameObjects'] if g.get('Name')=='Lights')
mutations=[]
for light in lights['Children']:
    if not light.get('Name','').startswith('Hall '):continue
    _,e,n=light['Name'].split();shadows=abs(float(e))==600 and float(n) in (-50,350)
    mutations.append(dict(tool='set_component',args=dict(id=light['__guid'],type='PointLight',properties=dict(LightColor='3.57,3.57,3.57,1',Temperature=5000,Shadows=shadows,Contribution='Diffuse, Transmissive'))))
gi=next(g for g in scene['GameObjects'] if g.get('Name')=='Ares bounced lighting')
mutations.append(dict(tool='set_component',args=dict(id=gi['__guid'],type='IndirectLightVolume',properties=dict(RuntimeIntensity=1.8,RuntimeContrast=.85))))
plan=dict(guards=manifest['guards'],files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()},scene_mutations=mutations,
    review=['hero-review.png','overview-review.png','floor-review.png','pump-review.png'],approved=False,
    original_imports_retained=True,original_physics_retained=True,additional_collision=manifest['additional_collision'])
(OUT/'install-plan.json').write_text(json.dumps(plan,indent=2))
print(json.dumps(dict(files=len(plan['files']),scene_mutations=len(mutations),additional_collision=manifest['additional_collision']),indent=2))
