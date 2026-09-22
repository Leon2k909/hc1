"""Recover the current M4 mesh and weights for removable factory sections."""
import sys, json, traceback
from pathlib import Path
import bpy
sys.path.insert(0, 'D:/tmp/hc1-mw22-tools')
from SourceIO.library.shared.content_manager import ContentManager
from SourceIO.library.source2 import CompiledModelResource
from SourceIO.library.utils import FileBuffer
from SourceIO.library.utils.tiny_path import TinyPath
from SourceIO.blender_bindings.source2.vmdl_loader import load_model, put_into_collections, ImportContext

here = Path(__file__).resolve().parent
source = Path('D:/SteamLibrary/steamapps/common/sbox/download/assets/models/weapons/sbox_assault_m4a1')
reports = []
for path in sorted(source.glob('*_m4a1.*.vmdl_c')):
    try:
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
        with FileBuffer(TinyPath(str(path))) as f:
            res = CompiledModelResource.from_buffer(f, TinyPath(str(path)))
        container = load_model(ContentManager(), res, ImportContext(scale=1, lod_mask=1))
        put_into_collections(container, path.stem)
        info = dict(file=path.name, bones=len(container.armature.data.bones) if container.armature else 0,
            objects=[dict(name=o.name, vertices=len(o.data.vertices), polygons=len(o.data.polygons),
                          materials=[m.name for m in o.data.materials]) for o in container.objects])
        reports.append(info)
        bpy.ops.wm.save_as_mainfile(filepath=str(here/(path.stem+'.blend')), compress=True)
        print('M4_IMPORT', json.dumps(info), flush=True)
    except Exception:
        traceback.print_exc()
(here/'current_m4_import.json').write_text(json.dumps(reports,indent=2))
