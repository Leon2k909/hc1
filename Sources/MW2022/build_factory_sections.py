"""Separate rigid factory pieces without changing the M4 animation rig."""
import bpy,json
from collections import defaultdict
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
HEADER='<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->\n'
reports=[]
for variant,source in [('view','v_m4a1.2e216481e1b73b07.blend'),('world','w_m4a1.838969e41b7004e4.blend')]:
    bpy.ops.wm.open_mainfile(filepath=str(HERE/source))
    obj=bpy.data.objects['m4a1_v_m4a1_b' if variant=='view' else 'm4a1_lod0_w_m4a1_LOD0']
    mesh=obj.data;mesh.calc_loop_triangles()
    keys=[tuple(round(x,4)for x in v.co)for v in mesh.vertices]
    parents={}
    def root(k):
        parents.setdefault(k,k)
        if parents[k]!=k:parents[k]=root(parents[k])
        return parents[k]
    for face in mesh.polygons:
        a=root(keys[face.vertices[0]])
        for vi in face.vertices:parents[root(keys[vi])]=a
    comps=defaultdict(list)
    for i,k in enumerate(keys):comps[root(k)].append(mesh.vertices[i].co)
    section={}
    for k,vs in comps.items():
        lo=[min(v[i]for v in vs)for i in range(3)];hi=[max(v[i]for v in vs)for i in range(3)]
        section[k]='barrel' if lo[0]>3.3 and hi[0]>6 else 'stock' if hi[0]<-4.03 and lo[2]>3 else 'reargrip' if hi[0]<-1.5 and hi[2]<5.7 else 'receiver'
    batches=defaultdict(lambda:defaultdict(list))
    for tri in mesh.loop_triangles:
        groups=[mesh.vertices[vi].groups for vi in tri.vertices]
        bone=obj.vertex_groups[max(groups[0],key=lambda g:g.weight).group].name if variant=='view' else 'weapon_root'
        assert variant=='world' or all(len([g for g in gs if g.weight>.001])==1 for gs in groups)
        kind=section[root(keys[tri.vertices[0]])]
        vs=[mesh.vertices[i].co for i in tri.vertices]
        if min(v.x for v in vs)>17.5:kind='flashhider'
        if variant=='world' and max(v.x for v in vs)<-1.55 and max(v.z for v in vs)<5.7:kind='reargrip'
        batches[bone][kind].append(tri)
    for bone,sections in batches.items():
        name=f'factory_{variant}_{bone}'
        folder=ROOT/'Assets/attachments/mw2022/factory'/name;folder.mkdir(parents=True,exist_ok=True)
        rel=folder.relative_to(ROOT/'Assets').as_posix()
        lines=[f'mtllib {name}.mtl'];faces=[];count=0
        for kind,tris in sections.items():
            fs=[]
            for tri in tris:
                ids=[]
                for li in tri.loops:
                    v=mesh.vertices[mesh.loops[li].vertex_index].co;n=mesh.corner_normals[li].vector;uv=mesh.uv_layers.active.data[li].uv
                    count+=1;ids.append(count)
                    lines.extend(['v %.7f %.7f %.7f'%(v.y,v.z,v.x),'vt %.7f %.7f'%tuple(uv),'vn %.7f %.7f %.7f'%(n.y,n.z,n.x)])
                fs.append('f '+' '.join(f'{i}/{i}/{i}'for i in ids))
            faces.extend(['o '+kind,'usemtl original']+fs)
        (folder/(name+'.obj')).write_text('\n'.join(lines+faces)+'\n')
        (folder/(name+'.mtl')).write_text('newmtl original\nKd 1 1 1\n')
        mat='v_m4a1_b' if variant=='view' else 'w_m4a1'
        meshes=', '.join('{ _class="RenderMeshFile" name="'+k+'" filename="'+rel+'/'+name+'.obj" import_translation=[0,0,0] import_rotation=[0,0,0] import_scale=1 align_origin_x_type="None" align_origin_y_type="None" align_origin_z_type="None" import_filter={exclude_by_default=true exception_list=["'+k+'"]} }' for k in sections)
        groups=', '.join('{_class="BodyGroup" name="'+k+'" children=[{_class="BodyGroupChoice" name="visible" meshes=["'+k+'"]},{_class="BodyGroupChoice" name="" meshes=[""]}]}'for k in sections if k!='receiver')
        (folder/(name+'.vmdl')).write_text(HEADER+'{rootNode={_class="RootNode" children=[{_class="MaterialGroupList" children=[{_class="DefaultMaterialGroup" remaps=[{from="original.vmat" to="models/weapons/sbox_assault_m4a1/'+mat+'.vmat"}] use_global_default=false}]},{_class="RenderMeshList" children=['+meshes+']},'+('{_class="BodyGroupList" children=['+groups+']}'if groups else '')+']}}')
        reports.append(dict(variant=variant,bone=bone,path=rel+'/'+name+'.vmdl',sections={k:len(v)for k,v in sections.items()}))
(HERE/'factory_sections.json').write_text(json.dumps(reports,indent=2))
print('FACTORY_SECTIONS',json.dumps(reports))
