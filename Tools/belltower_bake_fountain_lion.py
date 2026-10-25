"""Prepare the continuous lion sculpt, then reduce it in background Blender.

Normal Python: --prepare. Blender: --blender. A geometry signature ties the
cached source mesh to its procedural sculpt. Blender is not needed at runtime.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/fountain-ornaments-v2/sculpt-bake'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--blender', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else None)
    if args.prepare:
        import belltower_fountain_ornaments as O
        OUT.mkdir(parents=True, exist_ok=True)
        signature = O.lion_signature()
        vertices, faces, normals = O.sculpt_lion_mesh()
        path = OUT/(signature[:12]+'-high.npz')
        np.savez_compressed(path, vertices=vertices, faces=faces, normals=normals)
        request = {'signature': signature, 'input': str(path), 'target': str(O.lion_cache_path()),
                   'triangles': len(faces), 'target_triangles': 18000}
        (OUT/'request.json').write_text(json.dumps(request, indent=2)+'\n')
        print(json.dumps(request), flush=True)
    elif args.blender:
        import bpy
        request = json.loads((OUT/'request.json').read_text())
        target = Path(request['target'])
        assert not target.exists(), 'Keep the previous baked source.'
        with np.load(request['input']) as data:
            vertices, faces = data['vertices'], data['faces']
        bpy.ops.wm.read_factory_settings(use_empty=True)
        mesh = bpy.data.meshes.new('Continuous sculpt'); mesh.from_pydata(vertices, [], faces); mesh.update()
        obj = bpy.data.objects.new('Lion mask', mesh); bpy.context.scene.collection.objects.link(obj)
        bpy.context.view_layer.objects.active = obj; obj.select_set(True)
        modifier = obj.modifiers.new('Gameplay mesh reduction', 'DECIMATE')
        modifier.ratio = min(1., request['target_triangles']/len(faces))
        modifier.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        mesh = obj.data
        vertices = np.asarray([tuple(v.co) for v in mesh.vertices], np.float32)
        faces = np.asarray([tuple(p.vertices) for p in mesh.polygons], np.int32)
        assert faces.shape[1] == 3 and len(faces) <= request['target_triangles']+4
        adjacency = [[] for _ in vertices]
        for a, b, c in faces:
            adjacency[a].extend((b, c)); adjacency[b].extend((a, c)); adjacency[c].extend((a, b))
        unseen = set(range(len(vertices))); components = []
        while unseen:
            seed = unseen.pop(); component = {seed}; todo = [seed]
            while todo:
                for v in adjacency[todo.pop()]:
                    if v in unseen:
                        unseen.remove(v); component.add(v); todo.append(v)
            components.append(component)
        components.sort(key=len, reverse=True)
        assert all(len(c) <= 8 for c in components[1:]), 'Unexpected disconnected carving feature.'
        keep = sorted(components[0]); remap = np.full(len(vertices), -1, np.int32); remap[keep] = np.arange(len(keep))
        faces = remap[faces]; faces = faces[np.all(faces >= 0, axis=1)]; vertices = vertices[keep]
        # Preserve the oriented solid and compute smooth, area-weighted normals.
        normals = np.zeros_like(vertices)
        face_normals = np.cross(vertices[faces[:, 1]]-vertices[faces[:, 0]], vertices[faces[:, 2]]-vertices[faces[:, 0]])
        for k in range(3): np.add.at(normals, faces[:, k], face_normals)
        normals /= np.maximum(np.linalg.norm(normals, axis=1)[:, None], 1e-9)
        edges = np.sort(np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]]), axis=1)
        _, counts = np.unique(edges, axis=0, return_counts=True)
        assert np.all(counts == 2), 'The lion must remain a closed sculpt.'
        assert np.all(np.isfinite(vertices)) and np.all(np.isfinite(normals))
        target.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(target, vertices=vertices, faces=faces, normals=normals, signature=request['signature'])
        result = {**request, 'baked_triangles': len(faces), 'vertices': len(vertices),
                  'watertight_edges': True, 'connected_components': 1,
                  'sha256': hashlib.sha256(target.read_bytes()).hexdigest()}
        target.with_suffix('.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result), flush=True)
    else:
        parser.error('Choose --prepare or --blender.')


if __name__ == '__main__':
    main()
