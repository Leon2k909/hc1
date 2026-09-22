"""Install M4-specific optic models/materials while preserving shared SWB art."""
import json,re,uuid,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];A=ROOT/'Assets'
OUT=A/'attachments/m4a1/optics';OUT.mkdir(parents=True,exist_ok=True)
def guid(s):return str(uuid.uuid5(uuid.NAMESPACE_URL,'razed/m4a1/optic/'+s))
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf8')

def convert_smd(source,name,scale):
    # ModelDoc no longer imports SMD. Preserve the original UVs/normals in OBJ.
    lines=source.read_text().splitlines();i=lines.index('triangles')+1;triangles=[]
    while i<len(lines) and lines[i].strip()!='end':
        material=Path(lines[i].strip()).stem.lower();i+=1;vertices=[]
        for _ in range(3):
            fields=lines[i].split();i+=1
            p=list(map(float,fields[1:4]));n=list(map(float,fields[4:7]));uv=list(map(float,fields[7:9]))
            vertices.append(((p[1],-p[0],p[2]),(n[1],-n[0],n[2]),uv))
        a,b,c=[v[0] for v in vertices]
        ab=[b[i]-a[i] for i in range(3)];ac=[c[i]-a[i] for i in range(3)]
        cross=[ab[1]*ac[2]-ab[2]*ac[1],ab[2]*ac[0]-ab[0]*ac[2],ab[0]*ac[1]-ab[1]*ac[0]]
        length=math.sqrt(sum(x*x for x in cross))
        if length<1e-10:continue
        face_normal=[x/length for x in cross]
        fixed=[]
        for p,n,uv in vertices:
            length=math.sqrt(sum(x*x for x in n))
            n=[x/length for x in n] if length>1e-8 else face_normal
            if sum(n[i]*face_normal[i] for i in range(3))<=0:n=face_normal
            fixed.append((p,n,uv))
        triangles.append((material,fixed))
    points=[v[0] for _,tri in triangles for v in tri]
    low=[min(p[a] for p in points) for a in range(3)];high=[max(p[a] for p in points) for a in range(3)]
    center=[(low[a]+high[a])/2 for a in range(3)];center[2]=low[2]
    output=[f'mtllib {name}.mtl',f'o {name}'];index=1;materials=set()
    for mat,tri in triangles:
        output.append('usemtl '+mat);materials.add(mat)
        for p,n,uv in tri:
            x,y,z=[(p[a]-center[a])*scale for a in range(3)]
            # Both donor optics face -Y in the source. Rotate them to +X in-game.
            output.extend([f'v {-y:.8f} {z:.8f} {-x:.8f}',f'vt {uv[0]} {uv[1]}',f'vn {-n[1]} {n[2]} {-n[0]}'])
        output.append('f '+' '.join(f'{j}/{j}/{j}' for j in range(index,index+3)));index+=3
    destination=ROOT/f'Sources/M4A1/{name}_source.obj'
    destination.write_text('\n'.join(output)+'\n',encoding='utf8')
    (OUT/f'{name}.mtl').write_text('\n'.join(f'newmtl {m}\nKd 1 1 1' for m in sorted(materials))+'\n',encoding='utf8')
    print(name,'triangles',len(triangles),'bounds',[round((high[a]-low[a])*scale,3) for a in range(3)],'materials',sorted(materials))

# The authored lens and housing shaders live under Assets/shaders.
for name,mask in [('reflex','attachments/swb/sight/reflex/textures/red_dot_mask.png'),('tube','attachments/swb/sight/reflex/textures/red_dot_mask.png'),('scout','attachments/swb/sight/scope_hunter/textures/sniper_reticle.png')]:
    lens=(A/'attachments/swb/sight/reflex/textures/reflex_dot_shader.vmat').read_text(encoding='utf8')
    lens=lens.replace('shaders/swb_sam_red_dot.shader','shaders/m4_optic_lens.shader')
    lens=lens.replace('attachments/swb/sight/reflex/textures/red_dot_mask.png',mask)
    lens=lens.replace('g_flSightDistanceScale "3.000"','g_flSightDistanceScale "0.35"')
    if name=='scout':lens=lens.replace('//---- Glass ----','g_flScopeReticle "1"\n\t//---- Glass ----')
    (OUT/f'{name}_reticle.vmat').write_text(lens,encoding='utf8')

# Correct the source mesh's material names in private ModelDoc variants.
for name,source,scale,remaps in [
    ('reflex','reflex/w_reflex_sight',5.8,{'reflex_mat.vmat':'attachments/m4a1/optics/reflex_housing.vmat','reflex_glass.vmat':'attachments/m4a1/optics/reflex_reticle.vmat'}),
    ('scout','scope_hunter/w_scope_hunter_render',4.2,{'material.vmat':'attachments/m4a1/optics/scout_housing.vmat','material_001.vmat':'attachments/m4a1/optics/scout_housing.vmat','material_002.vmat':'attachments/m4a1/optics/scout_reticle.vmat'})]:
    data=(A/f'attachments/swb/sight/{source}.vmdl').read_text(encoding='utf8')
    convert_smd(A/f'attachments/swb/sight/{source}.smd',name,scale)
    remap='remaps = [ '+', '.join('{ from = "'+k+'" to = "'+v+'" }' for k,v in remaps.items())+' ]'
    data=re.sub(r'remaps\s*=\s*\[.*?\]',remap,data,flags=re.S)
    mesh=name+'_indexed'
    data=data.replace(f'attachments/swb/sight/{source}.smd',f'attachments/m4a1/optics/{mesh}.obj')
    data=data.replace('"BoundsCenter"','"None"')
    (OUT/f'{name}.vmdl').write_text(data,encoding='utf8')
housing=(A/'attachments/swb/sight/scope_hunter/textures/hunter.vmat').read_text(encoding='utf8')
housing=housing.replace('"shader"\t\t"shaders/complex.shader"','"shader" "shaders/m4_optic_housing.shader"')
(OUT/'scout_housing.vmat').write_text(housing,encoding='utf8')
housing=(A/'attachments/swb/sight/reflex/textures/reflex.vmat').read_text(encoding='utf8')
housing=housing.replace('shaders/complex.shader_c','shaders/m4_optic_housing.shader')
(OUT/'reflex_housing.vmat').write_text(housing,encoding='utf8')

specs=[('reflex','Reflex Sight','attachments/m4a1/optics/reflex.vmdl','-16.9,0,1.18','-19.28281,0,1.38177',1.0),
       ('tube','Patrol Red Dot','attachments/m4a1/tube_red_dot/tube_red_dot.vmdl','-16.9,0,1.18','-19.28281,0,1.38177',1.0),
       ('scout','Scout 3x','attachments/m4a1/optics/scout.vmdl','-17.7,0,1.18','-20.08281,0,1.38177',3.0)]
for name,title,model,offset,world_offset,mag in specs:
    aim={'reflex': '-2,-0.0066,-0.2075', 'tube': '-2,-0.0039,0.1073', 'scout': '0,0.0402,0.4999'}[name]
    path=f'gunsmith/m4a1/optics/{name}'
    components=[{'__type':'Sandbox.ModelRenderer','__guid':guid(name+'/model'),'Model':model,'Tint':'1,1,1,1'},
        {'__type':'Facepunch.Gunsmith.GunsmithSocketAttachment','__guid':guid(name+'/mount'),'SocketName':'muzzle',
         'SocketOffset':offset,'SocketAngles':'0,0,0','ModelSocketOffsets':{'models/weapons/sbox_assault_m4a1/w_m4a1.vmdl':world_offset}}]
    prefab={'RootObject':{'__guid':guid(name+'/root'),'Name':title,'Enabled':True,'Scale':'1,1,1','Components':components},'ResourceVersion':2,'__version':2}
    write(A/f'{path}.prefab',prefab)
    write(A/f'{path}.gnsmth',{'Name':title,'Category':'Optic','MainPrefab':{'_type':'gameobject','prefab':f'{path}.prefab'},
        'EligibleEquipment':['weapons/m4a1/m4a1.equip'],'RequiredLevel':0,'ModifyBodygroups':True,
        'Bodygroups':{'top_rail':3,'gasblock':1},'ModelBodygroups':{'models/weapons/sbox_assault_m4a1/w_m4a1.vmdl':{'top_rail':1,'gasblock':1}},
        'OverrideAimOffset':True,'OpticAimOffset':aim,'OpticMagnification':mag,'__references':[],'__version':0})
print('Installed Reflex Sight, Patrol Red Dot and Scout 3x')
world=A/'Weapons/M4A1/wm_m4a1.prefab'
data=json.loads(world.read_text());children=data['RootObject'].setdefault('Children',[])
if not any(any(c.get('Category')=='Optic' for c in child.get('Components',[])) for child in children):
    children.append({'__guid':guid('world-slot'),'Name':'Optic Attachment Point','Position':'0,0,10.3','Enabled':True,
        'Components':[{'__type':'Facepunch.Gunsmith.GunsmithAttachmentPoint','__guid':guid('world-component'),'Category':'Optic'}]})
    write(world,data)

# The original Holo/RMR exist only as viewmodel bodygroups. Retain their
# previous world appearance instead of applying invalid viewmodel indices.
for legacy in ('m4a1_optic_eotech', 'm4a1_optic_rmr'):
    path=A/f'gunsmith/m4a1/optics/{legacy}.gnsmth'
    data=json.loads(path.read_text())
    data.setdefault('ModelBodygroups', {})['models/weapons/sbox_assault_m4a1/w_m4a1.vmdl']={key:0 for key in data['Bodygroups']}
    write(path,data)
