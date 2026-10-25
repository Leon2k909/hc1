"""Retain complete near-LOD needle charts in intermediate fir geometry.

Only opaque wood is reduced. Original needle positions, UVs and normals are
copied directly from the verified OBJ, avoiding an alpha-card collapse pass.
No editor calls, bitmap generation, scene changes or distant-LOD changes.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import shutil
import sys

import bpy
import bmesh

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'Assets/models/maps/forestbase/fir'
WORK=ROOT/'output/forestbase/crown-work'
parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,default=ROOT/'output/forestbase/crown-stage/models/maps/forestbase/fir')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
args.output.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)


sys.path.insert(0,str(ROOT/'Tools'))
from forestbase_crown_obj import read_faces,write_faces


def prune_small_branches(obj,budget):
    """Keep complete woody islands, favouring visible area per triangle."""
    mesh=obj.data;mesh.calc_loop_triangles()
    if len(mesh.loop_triangles)<=budget:return
    parents=list(range(len(mesh.vertices)))
    def find(i):
        while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
        return i
    for edge in mesh.edges:
        a,b=map(find,edge.vertices)
        if a!=b:parents[b]=a
    groups={}
    for t in mesh.loop_triangles:
        g=groups.setdefault(find(t.vertices[0]),dict(vertices=set(),triangles=0,area=0))
        g['vertices'].update(t.vertices);g['triangles']+=1;g['area']+=t.area
    keep=set();used=0
    for g in sorted(groups.values(),key=lambda g:g['area']/g['triangles'],reverse=True):
        if used+g['triangles']<=budget:
            keep.update(g['vertices']);used+=g['triangles']
    assert keep,'Opaque component cannot fit its budget'
    bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in keep],context='VERTS')
    bm.to_mesh(mesh);bm.free();mesh.update()


statistics=[]
for variant in 'abc':
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    for mat in list(bpy.data.materials):bpy.data.materials.remove(mat)
    source=SOURCE/f'fir_{variant}_lod0.obj'
    bpy.ops.wm.obj_import(filepath=str(source),forward_axis='Y',up_axis='Z')
    tree=bpy.context.selected_objects[0];bpy.context.view_layer.objects.active=tree
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.separate(type='MATERIAL');bpy.ops.object.mode_set(mode='OBJECT')
    parts=[];wood_counts={}
    for part in [o for o in bpy.context.scene.objects if o.type=='MESH']:
        used={p.material_index for p in part.data.polygons}
        assert len(used)==1
        paint=part.data.materials[next(iter(used))].name
        if paint.endswith('_twig'):
            bpy.data.objects.remove(part,do_unlink=True);continue
        target=600 if paint.endswith('_bark') else 100 if paint.endswith('_dead_branches') else 500
        bpy.ops.object.select_all(action='DESELECT');part.select_set(True)
        bpy.context.view_layer.objects.active=part
        part.data.calc_loop_triangles();before=len(part.data.loop_triangles)
        if before>target:
            mod=part.modifiers.new('Opaque LOD only','DECIMATE')
            mod.ratio=target/before;mod.use_collapse_triangulate=True
            bpy.ops.object.modifier_apply(modifier=mod.name)
        prune_small_branches(part,target)
        part.data.calc_loop_triangles()
        wood_counts[paint]=dict(before=before,after=len(part.data.loop_triangles))
        parts.append(part)
    bpy.ops.object.select_all(action='DESELECT')
    for part in parts:part.select_set(True)
    bpy.context.view_layer.objects.active=parts[0];bpy.ops.object.join()
    wood=WORK/f'fir_{variant}_wood.obj'
    bpy.ops.wm.obj_export(filepath=str(wood),export_selected_objects=True,
        apply_modifiers=True,export_triangulated_mesh=True,forward_axis='Y',up_axis='Z')
    faces=read_faces(wood);near=read_faces(source)
    needle=f'fir_tree_01_twig';assert needle not in faces
    faces[needle]=near[needle]
    target=args.output/f'fir_{variant}_lod1.obj';write_faces(target,faces)
    mtl=SOURCE/f'fir_{variant}_lod1.mtl'
    if mtl.resolve()!=target.with_suffix('.mtl').resolve():shutil.copyfile(mtl,target.with_suffix('.mtl'))
    statistics.append(dict(variant=variant,wood=wood_counts,needleTriangles=len(near[needle]),
        triangles=sum(len(f) for f in faces.values()),
        sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        outputSha256=hashlib.sha256(target.read_bytes()).hexdigest()))
    print(json.dumps(statistics[-1]),flush=True)
(args.output/'crown-generation.json').write_text(json.dumps(statistics,indent=2)+'\n')
