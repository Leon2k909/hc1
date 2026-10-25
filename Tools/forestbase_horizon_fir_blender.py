"""Analyse/reduce dimensional fir branch islands for the distant forest.

Reuses source UVs and PBR atlases; never renders or accesses S&box.
"""
import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import bpy
import bmesh
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'Assets/models/maps/forestbase/fir'
parser=argparse.ArgumentParser();parser.add_argument('--analyze',action='store_true')
parser.add_argument('--output',type=Path,default=ROOT/'output/forestbase/forest-stage/models/maps/forestbase/fir')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
args.output.mkdir(parents=True,exist_ok=True)
statistics=[]
for variant in 'abc':
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    for material in list(bpy.data.materials):bpy.data.materials.remove(material)
    bpy.ops.wm.obj_import(filepath=str(SOURCE/f'fir_{variant}_distant.obj'),forward_axis='Y',up_axis='Z')
    tree=bpy.context.selected_objects[0];mesh=tree.data;mesh.calc_loop_triangles()
    parents=list(range(len(mesh.vertices)))
    def root(i):
        while parents[i]!=i:
            parents[i]=parents[parents[i]];i=parents[i]
        return i
    for edge in mesh.edges:
        a,b=map(root,edge.vertices)
        if a!=b:parents[b]=a
    groups={}
    for vertex in mesh.vertices:
        groups.setdefault(root(vertex.index),dict(vertices=[],triangles=0,materials=set(),area=0.))['vertices'].append(vertex.index)
    for triangle in mesh.loop_triangles:
        item=groups[root(triangle.vertices[0])];item['triangles']+=1;item['materials'].add(triangle.material_index)
        a,b,c=(mesh.vertices[i].co for i in triangle.vertices)
        item['area']+=(b-a).cross(c-a).length*.5
    coordinates=np.array([v.co[:] for v in mesh.vertices])
    for item in groups.values():
        xyz=coordinates[item['vertices']];item['min']=xyz.min(axis=0);item['max']=xyz.max(axis=0)
        item['center']=(item['min']+item['max'])/2
        item['leaf']=any(mesh.materials[m] and mesh.materials[m].name.endswith('_twig') for m in item['materials'])
    summary=dict(variant=variant,sourceTriangles=len(mesh.loop_triangles),islands=len(groups),
                 leafIslands=sum(g['leaf'] for g in groups.values()),
                 leafTriangleCounts=dict(Counter(g['triangles'] for g in groups.values() if g['leaf'])),
                 woodTriangleCounts=dict(Counter(g['triangles'] for g in groups.values() if not g['leaf'])))
    statistics.append(summary);print(json.dumps(summary),flush=True)
    if args.analyze:continue
    usable={i:g for i,g in groups.items() if g['triangles']}
    leaves={i:g for i,g in usable.items() if g['leaf']}
    wood={i:g for i,g in usable.items() if not g['leaf']}
    bounds_min=np.min([g['min'] for g in usable.values()],axis=0)
    bounds_max=np.max([g['max'] for g in usable.values()],axis=0)
    protected=set()
    # Retain the outer branch envelope in height/azimuth cells rather than
    # flattening the whole crown onto a handful of large vertical cards.
    height=bounds_max[1]-bounds_min[1]
    for band in range(18):
        candidates={i:g for i,g in leaves.items()
                    if band<=18*(g['center'][1]-bounds_min[1])/height<band+1}
        if not candidates:continue
        for angle in np.linspace(0,np.pi*2,16,endpoint=False):
            direction=np.array((np.cos(angle),0,np.sin(angle)))
            index=max(candidates,key=lambda i:float(np.max(coordinates[candidates[i]['vertices']]@direction)))
            protected.add(index)
    for axis in range(3):
        protected.add(min(usable,key=lambda i:usable[i]['min'][axis]))
        protected.add(max(usable,key=lambda i:usable[i]['max'][axis]))
    # The trunk is always retained, along with the large woody branches.
    for i,g in wood.items():
        if any('_trunk_' in mesh.materials[m].name for m in g['materials']):protected.add(i)
    protected.add(max(wood,key=lambda i:wood[i]['max'][1]-wood[i]['min'][1]))
    keep=set(protected)
    for candidates,budget in ((wood,800),(leaves,4200)):
        used=sum(g['triangles'] for i,g in candidates.items() if i in keep)
        assert used<=budget,(variant,'Protected envelope exceeds target',used,budget)
        ordered=sorted(candidates,key=lambda i:candidates[i]['area']/candidates[i]['triangles'],reverse=True)
        for i in ordered:
            if i in keep:continue
            cost=candidates[i]['triangles']
            if used+cost<=budget:keep.add(i);used+=cost
    original_area=sum(g['area'] for g in leaves.values())
    retained_area=sum(g['area'] for i,g in leaves.items() if i in keep)
    coverage_scale=min(1.35,float(np.sqrt(original_area/retained_area)))
    # Slightly broaden interior needle fans to retain coverage at distance.
    # Protected silhouette fans stay exact, and no fan exceeds source bounds.
    for i,g in leaves.items():
        if i not in keep or i in protected:continue
        center=g['center'];xyz=coordinates[g['vertices']];delta=xyz-center
        maximum=coverage_scale
        for axis in range(3):
            positive=delta[:,axis]>1e-8;negative=delta[:,axis]<-1e-8
            if positive.any():maximum=min(maximum,float(np.min((bounds_max[axis]-center[axis])/delta[positive,axis])))
            if negative.any():maximum=min(maximum,float(np.min((bounds_min[axis]-center[axis])/delta[negative,axis])))
        factor=max(1.,min(coverage_scale,maximum))
        for vertex,point in zip(g['vertices'],center+delta*factor):mesh.vertices[vertex].co=point
    keep_vertices={v for i in keep for v in usable[i]['vertices']}
    bm=bmesh.new();bm.from_mesh(mesh);bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[v for v in bm.verts if v.index not in keep_vertices],context='VERTS')
    bm.to_mesh(mesh);bm.free();mesh.update();mesh.calc_loop_triangles()
    assert 0<len(mesh.loop_triangles)<=5000
    assert mesh.uv_layers
    output=args.output/f'fir_{variant}_horizon.obj'
    bpy.ops.wm.obj_export(filepath=str(output),export_selected_objects=True,
                         apply_modifiers=True,export_triangulated_mesh=True,forward_axis='Y',up_axis='Z')
    text=output.read_text()
    assert '\nvt ' in text and not any('//' in line for line in text.splitlines() if line.startswith('f '))
    mtl=output.with_suffix('.mtl')
    mtl.write_text('\n'.join(line for line in mtl.read_text().splitlines() if not line.startswith('map_'))+'\n')
    summary.update(triangles=len(mesh.loop_triangles),retainedIslands=len(keep),
                   protectedIslands=len(protected),leafSurfaceAreaRetainedBeforeScaling=retained_area/original_area,
                   maximumInteriorFanScale=coverage_scale,
                   sourceMins=bounds_min.tolist(),sourceMaxs=bounds_max.tolist())
    print('REDUCED '+json.dumps(summary),flush=True)
(args.output/'branch-island-analysis.json').write_text(json.dumps(statistics,indent=2)+'\n')
