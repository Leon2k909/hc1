"""Keep the old watch deck as a model of its own: Assets/models/props/riverside/watch_deck_original/deck_original.vmdl.

The old deck was only ever geometry inside the Pad mesh. legacy_deck.py redraws it (812 triangles, identical to the Pad's own
vertices); this moves those vertices so the model's origin is the deck's centre on the pad (as watch_deck_v1's is) and writes
a one-LOD ModelDoc with the Pad's own materials (rs_wood, rs_concrete). Place it with a ModelRenderer at world
(-445, -60, 96), no rotation, and it sits exactly where the old deck stood. Nothing in the map uses it.
Only vertex lines move; UVs, normals and faces are the legacy file's, byte for byte.
"""
from pathlib import Path
import hashlib, json, sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).absolute().parents[3]
OUT = ROOT / 'output/riverside/watch-deck-v1'
SRC = OUT / 'legacy_deck_3bec244c.obj'
DEST = ROOT / 'Assets/models/props/riverside/watch_deck_original'
RES = 'models/props/riverside/watch_deck_original'
SHIFT = (60.0, -96.0, 445.0)          # OBJ axes (-e, z, n): the deck's centre on the pad is plan (60, -445, 96)

VMDL = '''<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->
{
	rootNode =
	{
		_class = "RootNode"
		children =
		[
			{
				_class = "MaterialGroupList"
				children =
				[
					{
						_class = "DefaultMaterialGroup"
						remaps =
						[
							{ from = "rs_concrete.vmat" to = "materials/riverside/rs_concrete.vmat" },
							{ from = "rs_wood.vmat" to = "materials/riverside/rs_wood.vmat" },
						]
						use_global_default = false
						global_default_material = ""
					},
				]
			},
{_class="RenderMeshList" children=[{_class="RenderMeshFile" name="original" filename="%s/deck_original.obj" import_scale=1 align_origin_x_type="None" align_origin_y_type="None" align_origin_z_type="None" import_filter={exclude_by_default=false exception_list=[]}},]},
		]
		model_archetype = ""
		primary_associated_entity = ""
		anim_graph_name = ""
		base_model_name = ""
	}
}
''' % RES


def main():
    lines = SRC.read_bytes().decode().splitlines(keepends=True)
    out, tris = [], 0
    for l in lines:
        if l.startswith('v '):
            x, y, z = (float(t) for t in l.split()[1:4])
            l = 'v %.3f %.3f %.3f\n' % (x + SHIFT[0], y + SHIFT[1], z + SHIFT[2])
        elif l.startswith('mtllib'):
            l = 'mtllib deck_original.mtl\n'
        elif l.startswith('o '):
            l = 'o deck_original\n'
        elif l.startswith('f '):
            tris += len(l.split()) - 3
        out.append(l)
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / 'deck_original.obj').write_text(''.join(out), newline='\n')
    (DEST / 'deck_original.mtl').write_text(SRC.with_suffix('.mtl').read_text(), newline='\n')
    (DEST / 'deck_original.vmdl').write_text(VMDL, newline='\n')
    info = dict(triangles=tris, resource=RES + '/deck_original.vmdl', position=[-445.0, -60.0, 96.0],
                files={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DEST.iterdir()) if p.is_file()})
    (OUT / 'original-manifest.json').write_text(json.dumps(info, indent=2))
    print(json.dumps(info, indent=1))


if __name__ == '__main__':
    main()
