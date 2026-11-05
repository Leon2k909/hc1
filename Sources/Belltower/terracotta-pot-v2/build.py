"""Review a wheel-thrown doorway pot without changing the saved town.

Uses the existing accepted clay material. Stage on C: temporary storage; native
s&box publishes the private review assets while the project is open.
"""
from pathlib import Path
from collections import Counter
import hashlib,json,math,re,sys,tempfile
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import belltower_detail as D
from belltower_move_square_lamps import geometry

OUT=Path(tempfile.gettempdir())/'belltower-terracotta-pot-v2'
STAGE=OUT/'stage'
RES='models/maps/belltower/terracotta-pot-v2'
MODEL=STAGE/'Assets'/RES
CENTRE_WORLD=(514.,1862.,0.)
PROFILE=np.array([
    (6.30,0.),(6.78,0.),(6.99,.16),(7.06,.48),(7.06,1.05),
    (7.14,1.55),(7.39,3.4),(7.71,5.8),(8.03,8.2),(8.36,10.6),
    (8.67,13.),(8.90,14.60),(9.08,14.88),(9.60,15.02),
    (9.99,15.28),(10.19,15.67),(10.24,16.22),(10.22,16.83),
    (10.11,17.34),(9.88,17.78),(9.56,18.),(9.29,17.94),
    (9.06,17.72),(8.96,17.37),(8.95,16.50),(8.81,15.10),
    (8.53,13.),(8.21,10.6),(7.88,8.2),(7.55,5.8),(7.22,3.4),
    (7.03,2.04),(6.84,1.65),(6.50,1.50),(.70,1.50),
    (.70,.70),(6.30,.70)
],float)

def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def shape(profile,sides):
    """A closed ceramic section: rolled lip, inner bowl, drain and recessed foot."""
    # Every LOD retains the same envelope and drain; detail is reduced by angle
    # and profile sampling, not by closing the mouth with a solid cylinder.
    angles=np.arange(sides)*2*math.pi/sides
    rr,zz=profile[:,0,None],profile[:,1,None]
    aa=angles[None,:]
    hand=.035*np.sin(3*aa+.27)+.024*np.sin(5*aa+zz*.14)
    hand*=np.minimum(1,zz/.6)*np.minimum(1,rr/3)
    # Local small chips on the outside of the rim, away from its inner edge.
    chip=np.zeros((len(profile),sides))
    for angle,width,depth in ((.76,.055,.13),(3.54,.042,.10)):
        delta=np.arctan2(np.sin(aa-angle),np.cos(aa-angle))
        chip+=depth*np.exp(-.5*(delta/width)**2)*np.exp(-.5*((zz-17.65)/.40)**2)*(rr>9.5)
    radius=rr+hand-chip
    x=radius*np.cos(aa);y=radius*np.sin(aa)
    z=np.broadcast_to(zz,x.shape).copy()
    z+=.025*np.sin(2*aa+.8)*np.exp(-.5*((zz-17.8)/1.3)**2)
    vertices=np.stack((x,y,z),axis=-1)
    # Surface derivatives follow the actual hand-formed surface. Seam normals
    # wrap exactly, and normals round the lip instead of rounding across it.
    da=np.roll(vertices,-1,axis=1)-np.roll(vertices,1,axis=1)
    dt=np.roll(vertices,-1,axis=0)-np.roll(vertices,1,axis=0)
    normals=np.cross(da,dt)
    normals/=np.linalg.norm(normals,axis=-1,keepdims=True)
    m=K.Model()
    for i in range(len(profile)):
        j=(i+1)%len(profile)
        for k in range(sides):
            kk=(k+1)%sides
            ids=((i,k),(i,kk),(j,kk),(j,k))
            D.outward(m,'clay_pot',[vertices[a,b] for a,b in ids],sum(normals[a,b] for a,b in ids),normals=[normals[a,b] for a,b in ids])
    m.material_overrides={'clay_pot':'materials/buildings/clay_pot.vmat'}
    return m,vertices

def modeldoc():
    text=(ROOT/'Assets/models/maps/lowtide/mooring_bollard_v2/mooring_bollard.vmdl').read_text()
    # Reuse only the installed engine's verified mesh/LOD schema.
    start=text.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"')
    end=text.index('\n\t\t]\n',start)
    children=text[start:end]
    children=re.sub(r'filename = "[^"]+mooring_bollard_lod([012])\.obj"',lambda m:f'filename = "{RES}/pot_lod{m[1]}.obj"',children)
    children=children.replace('switch_threshold = 30.0','switch_threshold = 12.0').replace('switch_threshold = 80.0','switch_threshold = 40.0')
    # Skip the reference model's materials and physics completely.
    return ('<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->\n'
        '{\n rootNode = { _class = "RootNode" children = [\n'
        '{ _class = "MaterialGroupList" children = [ { _class = "DefaultMaterialGroup" remaps = [ '
        '{ from = "clay_pot.vmat" to = "materials/buildings/clay_pot.vmat" } ] use_global_default = false global_default_material = "" } ] },\n'
        +children+'\n ] model_archetype = "" primary_associated_entity = "" anim_graph_name = "" base_model_name = "" }\n}\n')

def remove_original_pot():
    old=K.Model()
    D.lathe(old,(-1862.,514.),0.,[(7.,0.),(9.,15.),(10.2,15.5),(10.2,18.),(9.2,18.),(9.,16.5)],'clay_pot',sides=14)
    wanted=geometry(old)
    vmdl=ROOT/'Assets/models/maps/belltower/belltower_west.vmdl'
    reference='models/maps/belltower/compiler-safe/west/west_011_clay_pot.obj'
    source=ROOT/'Assets'/reference
    lines=source.read_bytes().splitlines(keepends=True)
    positions={};n=0;removed=set();found=Counter()
    for i,line in enumerate(lines):
        if line.startswith(b'v '):n+=1;positions[n]=line[2:].strip()
        elif line.startswith(b'f '):
            key=(b'clay_pot',frozenset(positions[int(t.split(b'/')[0])] for t in line.split()[1:]))
            if key in wanted:removed.add(i);found[key]+=1
    assert found==wanted and len(removed)==140,(sum(found.values()),sum(wanted.values()))
    (MODEL/'clay_without_one_pot.obj').write_bytes(b''.join(line for i,line in enumerate(lines) if i not in removed))
    (MODEL/'materials.mtl').write_bytes(source.with_name('materials.mtl').read_bytes())
    text=vmdl.read_text()
    assert text.count(reference)==1
    (MODEL/'west_without_one_pot.vmdl').write_text(text.replace(reference,RES+'/clay_without_one_pot.obj'))
    K.write_model(MODEL,RES,'old_pot',old_at_origin())
    return [vmdl,source,source.with_name('materials.mtl')]

def old_at_origin():
    m=K.Model()
    D.lathe(m,(0.,0.),0.,[(7.,0.),(9.,15.),(10.2,15.5),(10.2,18.),(9.2,18.),(9.,16.5)],'clay_pot',sides=14)
    m.material_overrides={'clay_pot':'materials/buildings/clay_pot.vmat'}
    return m

def main():
    MODEL.mkdir(parents=True,exist_ok=True)
    lods=[]
    selections=[list(range(len(PROFILE))),[0,1,3,4,5,7,9,11,12,13,14,16,18,20,22,24,26,29,31,33,34,35,36],[0,1,4,5,11,13,16,18,20,22,24,26,31,33,34,35,36]]
    for lod,(sides,ids) in enumerate(zip((64,32,16),selections)):
        m,vertices=shape(PROFILE[ids],sides)
        count=K.write_obj(MODEL/f'pot_lod{lod}.obj',m,f'pot_lod{lod}')
        # A real closed ring grid has two incident faces at every edge.
        assert np.isfinite(vertices).all()
        assert count==2*sides*len(ids)
        assert vertices[:,:,2].min()>-.001 and vertices[:,:,2].max()<18.04
        lods.append({'triangles':count,'segments':sides,'profile_rings':len(ids)})
    (MODEL/'terracotta_pot.vmdl').write_text(modeldoc())
    guards=remove_original_pot()
    guards += [ROOT/'Assets/scenes/maps/Belltower/belltower.scene',ROOT/'Assets/materials/buildings/clay_pot.vmat',ROOT/'Tools/belltower_map.py',ROOT/'Tools/belltower_detail.py']
    guard={p.relative_to(ROOT).as_posix():sha(p) for p in guards}
    files={p.relative_to(STAGE).as_posix():sha(p) for p in STAGE.rglob('*') if p.is_file()}
    report={'revision':'belltower-terracotta-pot-v2','review_only':True,'stage':str(STAGE),'files':files,'guards':guard,'lods':lods,'world_position':CENTRE_WORLD,'original_triangles':140,'existing_clay_material_unchanged':True,'collision_unchanged':True,'envelope_inches':[20.6,20.6,18.04],'source_sha256':sha(Path(__file__))}
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('revision','stage','lods','original_triangles','review_only')}))

if __name__=='__main__':main()
