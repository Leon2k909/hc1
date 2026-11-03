"""Build a review candidate without changing the published map or open scene."""
from pathlib import Path
from collections import Counter
import sys, json, hashlib, shutil, re, pickle
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'Tools'))
import map_kit as K
import riverdale_hall as H
import riverdale_materials as RM
import riverdale_camera as C
import riverdale_splice as S
sys.path.insert(0, str(Path(__file__).resolve().parent))
import native

OUT = native.OUT
STAGE = OUT/'stage'
STAGE.mkdir(parents=True, exist_ok=True)
ASSET = 'models/maps/riverdale/cctv_v2_review'
MATERIAL = 'materials/riverdale/cctv_v2'
TEXTURES = ROOT/'Assets'/MATERIAL
TEXTURES.mkdir(parents=True, exist_ok=True)

def write_asset(path, text):
    result = native.large_call('write_file', dict(path='Assets/'+path, content=text))
    assert result.get('written'), result

def textures():
    rng = np.random.default_rng(1647)
    n = 512
    noise = rng.normal(0, 1.0, (n, n))
    coarse = np.array(Image.fromarray(rng.integers(0, 256, (32,32), dtype=np.uint8)).resize((n,n), Image.Resampling.BICUBIC), float)/255-.5
    configs = {C.PAINT: ((178,181,174), .60, .0), C.SEAL: ((29,32,31), .70, .0),
               C.METAL: ((122,128,128), .36, 1.), C.GLASS: ((12,30,36), .13, .0),
               C.INNER: ((18,21,20), .48, .0)}
    for name, (color, rough, metal) in configs.items():
        variation = noise*.7+coarse*7
        rgb = np.clip(np.array(color)[None,None,:]+variation[:,:,None], 0,255).astype('uint8')
        Image.fromarray(rgb).save(TEXTURES/f'{name}_color.png')
        roughness = np.clip((rough+coarse*.055+noise*.003)*255,0,255).astype('uint8')
        Image.fromarray(roughness).save(TEXTURES/f'{name}_rough.png')
        vmat = f'''"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    g_flMetalness "{metal}"
    g_flRoughnessScaleFactor "1"
    TextureColor "{MATERIAL}/{name}_color.png"
    TextureNormal "materials/default/default_normal.tga"
    TextureRoughness "{MATERIAL}/{name}_rough.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_vColorTint "[1 1 1 1]"
    g_flModelTintAmount "1"
}}
'''
        write_asset(f'{MATERIAL}/{name}.vmat', vmat)
    label = Image.new('RGB',(1024, 352),(184,185,174))
    d = ImageDraw.Draw(label)
    font = ImageFont.truetype('C:/Windows/Fonts/consola.ttf',64)
    small = ImageFont.truetype('C:/Windows/Fonts/consola.ttf',42)
    d.rectangle((17,17,1007,335), outline=(76,80,77), width=5)
    d.text((55,40), 'CAM-07  /  IP66', font=font, fill=(45,52,49))
    d.text((55,120), '24V DC   FIXED OPTICS', font=small, fill=(62,68,64))
    d.text((55,190), 'SECURITY  /  SERVICE 03', font=small, fill=(62,68,64))
    for x in range(60, 960, 7):
        d.line((x,273,x,310), fill=(65,68,63), width=int(rng.integers(1,5)))
    label.save(TEXTURES/f'{C.LABEL}_color.png')
    write_asset(f'{MATERIAL}/{C.LABEL}.vmat', f'''"Layer0"
{{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 g_flMetalness "0"
 TextureColor "{MATERIAL}/{C.LABEL}_color.png"
 TextureNormal "materials/default/default_normal.tga"
 TextureRoughness "[0.65 0.65 0.65 0]"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_vColorTint "[1 1 1 1]"
}}
''')

def main():
    # Capture only the old camera function's exact polygons, independently of the
    # hall build. Nothing else from a regenerated map is used in the candidate.
    old_d, old_f, new_d, new_f = (K.Model() for _ in range(4))
    original = H.camera
    placements = []
    def record(d, fine, face, s, z, target):
        original(old_d, old_f, face, s, z, target)
        centre = C.camera(new_d, new_f, face, s, z, target)
        placements.append(dict(at=list(K.to_world(face.p(s,z))), centre=list(K.to_world(centre)),
                               out=list(K.to_world(face.out)), target=list(K.to_world(target))))
    cache = OUT/'old-camera-geometry.pickle'
    if cache.exists():
        old_d, old_f, records = pickle.loads(cache.read_bytes())
        for point, out, s, z, target in records:
            face = H.Face(point, out)
            centre = C.camera(new_d, new_f, face, s, z, target)
            placements.append(dict(at=list(K.to_world(face.p(s,z))), centre=list(K.to_world(centre)),
                                   out=list(K.to_world(face.out)), target=list(K.to_world(target))))
    else:
        records = []
        def record_cached(d, fine, face, s, z, target):
            records.append((face.o, face.out, s, z, target))
            record(d, fine, face, s, z, target)
        H.camera = record_cached
        H.build()
        H.camera = original
        cache.write_bytes(pickle.dumps((old_d,old_f,records)))
    print(f'Captured {len(placements)} hall camera placements', flush=True)
    report = dict(placements=placements, models=[])
    for suffix, old, new in [('detail',old_d,new_d), ('fine',old_f,new_f)]:
        name = f'riverdale_hall_{suffix}'
        source = ROOT/'Assets/models/maps/riverdale'/f'{name}.obj'
        for paint in old.polygons:
            old.tile_overrides[paint] = RM.TILES.get(paint, 64.0)
        oldpath, newpath = STAGE/f'{name}-old.obj', STAGE/f'{name}-new.obj'
        K.write_obj(oldpath, old, name)
        if new.polygons: K.write_obj(newpath, new, name)
        header, published = S.read_obj(source)
        _, oldfaces = S.read_obj(oldpath)
        newfaces = S.read_obj(newpath)[1] if new.polygons else []
        have, remove = Counter(published), Counter(oldfaces)
        missing = remove-have
        assert not missing, f'{name}: {sum(missing.values())} camera faces do not match published geometry'
        result = list((have-remove).elements())+newfaces
        target = STAGE/f'{name}.obj'
        S.write_obj(target, header, result)
        target.with_suffix('.mtl').write_text(''.join(f'newmtl {m}\nKd 1 1 1\nd 1\n' for m in sorted({m for m,_ in result})))
        # Keep the published modeldoc geometry/physics/material configuration.
        # Only the source OBJ path and the camera's new material slots change.
        vmdl_path = source.with_suffix('.vmdl')
        text = vmdl_path.read_text()
        text = text.replace(f'models/maps/riverdale/{name}.obj', f'{ASSET}/{name}.obj')
        text = text.replace(f'"models/maps/riverdale/{name}_hulls_', f'"models/maps/riverdale/{name}_hulls_')
        if new.polygons:
            lines = text.splitlines(keepends=True)
            last = max(i for i,line in enumerate(lines) if 'from = ' in line and 'to = ' in line)
            lines[last] = lines[last].rstrip().rstrip(',')+',\n'
            adds = [f'\t\t\t\t\t\t\t{{ from = "{paint}.vmat" to = "{MATERIAL}/{paint}.vmat" }}' for paint in sorted(new.polygons)]
            lines[last+1:last+1] = [line+(',\n' if i<len(adds)-1 else '\n') for i,line in enumerate(adds)]
            text = ''.join(lines)
        (STAGE/f'{name}.vmdl').write_text(text)
        report['models'].append(dict(name=name, source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
            old_camera_triangles=len(oldfaces), new_camera_triangles=len(newfaces),
            unchanged_triangles=len(published)-len(oldfaces), candidate_triangles=len(result),
            unrelated_faces_preserved=Counter(result)-Counter(newfaces)==have-remove,
            source_vmdl_sha256=hashlib.sha256(vmdl_path.read_bytes()).hexdigest()))
        print(f'{name}: removed {len(oldfaces)}, added {len(newfaces)}; preserved {len(published)-len(oldfaces)} faces', flush=True)
    if '--rebase' not in sys.argv:
        textures()
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    copy_lines = []
    for entry in report['models']:
        name = entry['name']
        for ext in ('obj','mtl','vmdl'):
            src = (STAGE/f'{name}.{ext}').as_posix()
            dst = (ROOT/'Assets'/ASSET/f'{name}.{ext}').as_posix()
            copy_lines.append(f'System.IO.File.Copy(@"{src}", @"{dst}.cctv-writing", true); System.IO.File.Move(@"{dst}.cctv-writing", @"{dst}", true);')
    destination = (ROOT/'Assets'/ASSET).as_posix()
    script = OUT/'publish-review.cs.txt'
    script.write_text(f'System.IO.Directory.CreateDirectory(@"{destination}");\n'+'\n'.join(copy_lines)+'\nreturn "Review model sources written; published models unchanged";\n')
    print(json.dumps(native.script(script),indent=2),flush=True)
    print(json.dumps(report['models'],indent=2), flush=True)

if __name__=='__main__': main()
