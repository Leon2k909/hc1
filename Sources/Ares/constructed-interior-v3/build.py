"""One guarded native-preview revision; no public asset is overwritten."""
from pathlib import Path
from collections import Counter
import sys,json,hashlib,re,shutil
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,ares_map as A,ares_interior as I,riverdale_splice as S
import geometry as G
import collision as C
OUT=ROOT/'output/ares/constructed-interior-v3';STAGE=OUT/'stage';OUT.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(path,text):
    p=STAGE/path;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8',newline='');return p
guards={}
for rel in ('Assets/models/maps/ares/ares_hall.vmdl','Assets/models/maps/ares/ares_reactor.vmdl',
            'Assets/models/maps/ares/ares_reactor.obj','Assets/models/maps/ares/pressure-doors-v2/hall_base.obj',
            'Assets/scenes/maps/Ares/ares.scene','Tools/ares_interior.py','Tools/ares_map.py'):
    p=ROOT/rel;guard=OUT/'before'/rel;guard.parent.mkdir(parents=True,exist_ok=True)
    if guard.exists():assert sha(p)==sha(guard),'Source changed: '+rel
    else:shutil.copy2(p,guard)
    guards[rel]=sha(p)
def faces(m,name,path):
    G.config(m);I.configure(m)
    # G's private materials win over the old paint configuration.
    for p,d in G.MATERIALS.items():
        if p in m.polygons:m.material_overrides[p]=d
    K.write_obj(path,m,name)
    return S.read_obj(path)[1]
old=K.Model()
for e in (-900,-500,500,900):I.portal(old,e)
for side in (-1,1):
    for n in (-600,-150,300):I.side_haunch(old,side,n)
I.galleries(old);I.service_runs(old);I.work_lights(old);I.floor(old)
for n in (-500.,-100.,300.,700.):old.box((-1100,n-5,706),(1100,n+5,720),'ar_steel')
removed=Counter(faces(old,'ares_hall',OUT/'hall-removed.obj'))
base=ROOT/'output/ares/surface-finish-v2/stage/Assets/models/maps/ares/surface-finish-v2/hall_trial.obj'
header,published=S.read_obj(base);have=Counter(published);missing=removed-have
assert not missing,f'{sum(missing.values())} removal faces missing: {Counter(m for m,c in missing.elements())}'
new=K.Model()
for e in (-900,-500,500,900):G.portal(new,e)
for side in (-1,1):
    for n in (-600,-150,300):G.haunch(new,side,n)
G.ceiling(new);G.galleries(new);G.floor(new)
assert not new.boxes and not new.hulls
add=faces(new,'ares_hall',OUT/'hall-added.obj')
folder='Assets/models/maps/ares/constructed-v3/'
retained=list((have-removed).elements());quiet_treads=0;result=[]
for paint,corners in retained:
    pts=[list(map(float,p.split())) for p,uv,n in corners]
    if paint=='ar_hazard' and all(759.9<=abs(p[0])<=880.1 and -470.1<=p[2]<=-157.9 and 12<=p[1]<=198 for p in pts):
        paint=G.DARK;quiet_treads+=1
    result.append((paint,corners))
result+=add
p=STAGE/folder/'hall.obj';p.parent.mkdir(parents=True,exist_ok=True)
S.write_obj(p,[l.replace('hall_trial.mtl','hall.mtl') for l in header],result)
put(folder+'hall.mtl',''.join(f'newmtl {m}\nKd 1 1 1\n' for m in sorted({m for m,c in result})))
print('Hall',len(published),'-',sum(removed.values()),'+',len(add),'=',len(result),flush=True)

# Retain the current reactor's exact glass/plasma, four existing signs, lamp
# ring and top stack. Replace its flat mechanical body and all four box pumps.
_,published_core=S.read_obj(ROOT/'Assets/models/maps/ares/ares_reactor.obj')
old_pumps=K.Model()
for e,n in ((270,270),(-270,270),(-270,-270),(270,-270)):
    I.pump_unit(old_pumps,e,n,np.degrees(np.arctan2(n,e))+90)
pump_faces=Counter(faces(old_pumps,'ares_reactor',OUT/'pumps-removed.obj'))
core_have=Counter(published_core);assert not pump_faces-core_have,'Pump source differs'
retained=list((core_have-pump_faces).elements());kept=[];dropped=[]
for mat,c in retained:
    # Visible glass/plasma/signs remain exact. Keep the flared ring, stack and
    # copper pipes while new fabricated housings replace flat band surfaces.
    z=[float(p.split()[1]) for p,uv,n in c]
    keep=mat in ('ar_plasma','ar_core','ar_signs','ar_copper','ar_led_warm','ar_led_amber') or min(z)>=559
    if keep:kept.append((mat,c))
    else:dropped.append((mat,c))
core=K.Model();G.reactor(core);assert not core.boxes and not core.hulls
added_core=faces(core,'ares_reactor',OUT/'reactor-added.obj')
core_result=kept+added_core
p=STAGE/folder/'reactor.obj';p.parent.mkdir(parents=True,exist_ok=True)
S.write_obj(p,['# Constructed Ares reactor\n','mtllib reactor.mtl\n'],core_result)
put(folder+'reactor.mtl',''.join(f'newmtl {m}\nKd 1 1 1\n' for m in sorted({m for m,c in core_result})))
print('Reactor',len(published_core),'-',sum(pump_faces.values()),'-',len(dropped),'+',len(added_core),'=',len(core_result),flush=True)

for model,name in [('hall','hall'),('reactor','reactor')]:
    doc=(ROOT/f'Assets/models/maps/ares/ares_{model}.vmdl').read_text()
    primary=re.findall(r'filename\s*=\s*"([^"]+)"',doc)[0]
    doc=doc.replace(primary,'models/maps/ares/constructed-v3/'+name+'.obj',1)
    # Keep only the useful generated albedo/normal work from the rejected v2
    # trial. Structural painted metal is now geometry with restrained coating.
    for m in ('floor','frame'):
        doc=doc.replace('materials/ares/interior-v1/'+m+'.vmat','materials/ares/surface-finish-v2/'+m+'.vmat')
    for m in ('steel','gunmetal','grating'):
        doc=doc.replace('materials/ares/ar_'+m+'.vmat','materials/ares/surface-finish-v2/'+m+'.vmat')
    mats=dict(G.MATERIALS)
    if model=='hall':mats['ar_in_wall']='materials/ares/surface-finish-v2/wall.vmat'
    token=doc.index('[',doc.index('remaps ='))+1
    doc=doc[:token]+''.join('\n{ from = "'+m+'.vmat" to = "'+v+'" },' for m,v in mats.items())+doc[token:]
    put(folder+'ares_'+model+'_trial.vmdl',C.augment(doc,model,STAGE))

configs={G.PAINT:('panel','0.86 0.84 0.8 1',0,.85),G.DARK:('frame','1.25 1.25 1.2 1',0,1),
 G.STEEL:('alloy','0.87 0.84 0.79 1',.5,1.12),G.RED:('red','1.1 0.94 0.86 1',0,.85),
 G.RUBBER:('dark','0.7 0.7 0.7 1',0,1),G.COPPER:('frame','3.6 1.4 0.55 1',.25,.75),
 G.CEILING:('panel','0.62 0.58 0.55 1',0,1)}
for material,(source,tint,metal,rough) in configs.items():
    text=(ROOT/f'Assets/materials/ares/interior-v1/{source}.vmat').read_text()
    text=re.sub(r'g_flMetalness "[^"]+"',f'g_flMetalness "{metal}"',text)
    text=re.sub(r'g_flRoughnessScaleFactor "[^"]+"',f'g_flRoughnessScaleFactor "{rough}"',text)
    text=re.sub(r'g_vColorTint "[^"]+"',f'g_vColorTint "[{tint}]"',text)
    put('Assets/'+G.MATERIALS[material],text)
text=(ROOT/'Assets/materials/ares/surface-finish-v2/floor.vmat').read_text()
text=text.replace('g_vColorTint "[1 1 1 1]"','g_vColorTint "[0.83 0.92 1 1]"').replace('g_flRoughnessScaleFactor "0.57"','g_flRoughnessScaleFactor "0.48"')
put('Assets/'+G.MATERIALS[G.FLOOR],text)
put('Assets/'+G.MATERIALS[G.SKIN],'''"Layer0"
{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 g_flMetalness "0"
 g_flRoughnessScaleFactor "1"
 TextureColor "materials/ares/constructed-v3/skin_color.png"
 TextureNormal "materials/ares/interior-v1/panel_normal.png"
 TextureRoughness "materials/ares/constructed-v3/skin_rough.png"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_vColorTint "[1 1 1 1]"
 g_flModelTintAmount "1"
}
''')
manifest=dict(guards=guards,files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()},
    hall=dict(before=len(published),removed=sum(removed.values()),added=len(add),after=len(result),retained_exact=len(published)-sum(removed.values())-quiet_treads,quiet_tread_faces=quiet_treads),
    reactor=dict(before=len(published_core),retained_exact=len(kept),removed=len(dropped)+sum(pump_faces.values()),added=len(added_core),after=len(core_result)),
    all_existing_collision_retained=True,additional_collision=dict(hall_support_boxes=28,reactor_skirt_hulls=1),scene_unchanged=True)
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
print('Staged',len(manifest['files']),'files',flush=True)
