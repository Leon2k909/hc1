"""A continuous precast entry stair shell with molded nosings, grip grooves and localized edge chips."""
from pathlib import Path
import json,math,sys
import numpy as np
ROOT=Path(sys.argv[1]).resolve();sys.dont_write_bytecode=True;sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
K.obj_vector=lambda p:f'{p[1]:.5f} {p[2]:.5f} {p[0]:.5f}'
MODEL='models/props/riverside/t2_precast_entry_v1';MAT='materials/riverside/t2_precast_entry_v1/weathered.vmat'
OUT=ROOT/'Assets'/MODEL;REPORT=ROOT/'output/riverside/t2-precast-entry-v1';OUT.mkdir(parents=True,exist_ok=True);REPORT.mkdir(parents=True,exist_ok=True)
def plan(p):return np.array((-p[1],p[0],p[2]),float)
X,Y,Z=[plan(p) for p in ((1,0,0),(0,1,0),(0,0,1))]
def profile(lod):
    pts=[(0,0)];nose=[]
    for step in range(4):
        x=step*10;z=(step+1)*7.25
        pts.append((x,z-.30));nose.append((len(pts)-1,step,0))
        pts.append((x+.12,z-.10));nose.append((len(pts)-1,step,.5))
        pts.append((x+.32,z));nose.append((len(pts)-1,step,1))
        if lod<2:
            for offset in ((1.35,2.15,2.95) if lod==0 else (1.35,2.95)):
                q=x+offset;pts.extend(((q,z),(q+.055,z-.085),(q+.18,z-.085),(q+.235,z)))
        pts.append((x+10,z))
    pts.extend(((40,0),));return np.array(pts,float),nose
def make(lod):
    m=K.Model();p,noses=profile(lod);ys=np.linspace(-18,18,(25,9,2)[lod]);rows=[]
    for y in ys:
        q=p.copy()
        if lod<2:
            for index,step,top in noses:
                wear=.04*(.5+.5*math.sin(y*.8+step*2.1))
                # Two small damaged outside corners; the centre walking line keeps exact rise/going.
                chip=(.85*max(0,(y-15)/3)**2 if step==0 else .55*max(0,(-y-15)/3)**2 if step==1 else 0)
                q[index,0]+=(wear+chip)*(.3+.7*top)
                q[index,1]-=(wear+chip)*(.15+.22*top)
        rows.append([plan((x,y,z)) for x,z in q])
    for row0,row1 in zip(rows,rows[1:]):
        for k,((x,z),(xx,zz)) in enumerate(zip(p,np.roll(p,-1,axis=0))):
            normal=plan((-(zz-z),0,xx-x))
            G.card(m,'concrete',[row0[k],row1[k],row1[(k+1)%len(p)],row0[(k+1)%len(p)]],normal)
    # Concave caps are triangulated, avoiding overlapping boxes and buried internal faces.
    for row,y,normal in ((rows[0],ys[0],-Y),(rows[-1],ys[-1],Y)):
        cap_profile=[(K.to_world(v)[0],K.to_world(v)[2]) for v in row]
        G._cap(m,'concrete',row,cap_profile,normal)
    m.material_overrides['concrete']=MAT;m.tile_overrides['concrete']=64
    for i,(pts,n) in enumerate(m.polygons['concrete']):
        ep=np.array([K.to_world(v) for v in pts]);en=K.to_world(n)
        if abs(en[2])>.7:
            uv=[((v[1]+18)/64+.17,(v[0]+5)/64+.25) for v in ep]
        elif abs(en[0])>.7:
            uv=[((v[1]+18)/64+.17,v[2]/36) for v in ep]
        else:uv=[(v[0]/64+.17,v[2]/36) for v in ep]
        m.polygon_uvs[('concrete',i)]=uv
    return m
if __name__=='__main__':
    counts=[]
    for k in range(3):counts.append(K.write_obj(OUT/f'entry_lod{k}.obj',make(k),'precast_entry'))
    meshes=','.join('{_class="RenderMeshFile" name="lod%d" filename="%s/entry_lod%d.obj" import_translation=[0,0,0] import_rotation=[0,0,0] import_scale=1 align_origin_x_type="None" align_origin_y_type="None" align_origin_z_type="None" import_filter={exclude_by_default=false exception_list=[]}}'%(i,MODEL,i) for i in range(3))
    (OUT/'entry_steps.vmdl').write_text('''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{rootNode={_class="RootNode" children=[{_class="MaterialGroupList" children=[{_class="DefaultMaterialGroup" remaps=[{from="concrete.vmat" to="materials/riverside/t2_precast_entry_v1/weathered.vmat"}] use_global_default=false global_default_material=""}]},{_class="RenderMeshList" children=[%M%]},{_class="LODGroupList" children=[{_class="LODGroup" switch_threshold=0 meshes=["lod0"]},{_class="LODGroup" switch_threshold=18 meshes=["lod1"]},{_class="LODGroup" switch_threshold=45 meshes=["lod2"]}]}]}}
'''.replace('%M%',meshes))
    r=dict(triangles=counts,new_materials=1,new_textures=0,shared_approved_material=MAT,width=36,depth=40,height=29,risers=4,installed=False)
    (REPORT/'mesh-report.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
