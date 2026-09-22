"""Decode VTFs and translate referenced Source materials to s&box materials.

Phong exponent -> perceptual roughness is an approximation, not recovered MWII PBR.
Original VMT/VTF files remain in the extracted workshop packs.
"""
import argparse
import json
import math
import sys
import traceback
from pathlib import Path

import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ASSETS = ROOT/'Assets'
parser = argparse.ArgumentParser()
parser.add_argument('--tools', type=Path, default=Path('D:/tmp/hc1-mw22-tools'))
args = parser.parse_args()
sys.path.insert(0, str(args.tools))
from SourceIO.library.shared.app_id import SteamAppId
from SourceIO.library.shared.content_manager import ContentManager
from SourceIO.library.shared.content_manager.providers.loose_files import LooseFilesContentProvider
from SourceIO.library.source1.vmt import VMT
from SourceIO.library.utils import FileBuffer
from SourceIO.library.utils.tiny_path import TinyPath
from SourceIO.library.utils.pylib.vtf import load_vtf_texture

inventory = json.loads((HERE/'inventory.json').read_text())
cm = ContentManager()
providers = [LooseFilesContentProvider(TinyPath(p['extracted']), SteamAppId(4000)) for p in inventory['packs']]
cm.children.update(providers)
cm.priority_list = providers
materials, failures, texture_report, notes = {}, [], {}, []


def normalized(path):
    return str(path).replace('\\','/').strip().lower()


def read_pixels(source):
    buffer = cm.find_file(TinyPath('materials') / (normalized(source).removesuffix('.vtf')+'.vtf'))
    if buffer is None:
        raise FileNotFoundError(source)
    data, w, h, floating = load_vtf_texture(buffer.read())
    array = np.frombuffer(data, np.float32 if floating else np.uint8).reshape(h,w,4).copy()
    if floating:
        array = np.uint8(np.clip(array,0,1)*255)
    return array


def texture(source, role):
    key = (normalized(source), role)
    if str(key) in texture_report:
        return texture_report[str(key)]['path']
    relative = 'attachments/mw2022/textures/'+normalized(source).removesuffix('.vtf')+'_'+role+'.png'
    destination = ASSETS/relative
    destination.parent.mkdir(parents=True,exist_ok=True)
    pixels = read_pixels(source)
    if role == 'normal':
        pixels[:,:,1] = 255-pixels[:,:,1]
        pixels = pixels[:,:,:3]
    elif role == 'color':
        pixels = pixels[:,:,:3]
    elif role == 'opacity':
        pixels = pixels[:,:,3]
    elif role == 'roughness':
        exponent = pixels[:,:,0].astype(np.float32)
        pixels = np.uint8(np.clip(np.power(2/(exponent+2),0.25),.18,.85)*255)
    Image.fromarray(pixels).save(destination)
    texture_report[str(key)] = dict(source=source, role=role, path=relative,
                                    width=pixels.shape[1],height=pixels.shape[0])
    return relative


def convert(full):
    if any(s in full for s in ('reticle_ui_stencil', 'stencil_outline', 'vm_depth_mask')):
        destination=ASSETS/'attachments/mw2022/materials'/(full+'.vmat')
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_text((ASSETS/'attachments/m4a1/materials/hidden.vmat').read_text())
        notes.append(dict(material=full,note='Source runtime stencil geometry is transparent; s&box lens supplies its own reticle.'))
        return dict(source=full,shader='runtime stencil',hidden=True,vmat=destination.relative_to(ASSETS).as_posix())
    buffer = cm.find_file(TinyPath('materials')/(full+'.vmt'))
    if buffer is None:
        raise FileNotFoundError(full+'.vmt')
    vmt = VMT(buffer,full,cm)
    color = vmt.get_string('$basetexture',None)
    normal = vmt.get_string('$bumpmap',None)
    exponent = vmt.get_string('$phongexponenttexture',None)
    if normal and '${' in normal:
        notes.append(dict(material=full,note='Original VMT contains an unresolved normal-map placeholder; use flat normal.',original=normal))
        normal = None
    glass = any(s in full for s in ('lens','lense','glass'))
    optic_glass = glass and ('optic' in full or 'sight' in full or any(s in full for s in ('reflex','holo','4x','thermal','scope','hybrid','reddot')))
    record = dict(source=full, shader=vmt.shader, glass=glass, optic_glass=optic_glass,
                  color=texture(color,'color') if color else None,
                  normal=texture(normal,'normal') if normal else None,
                  roughness=texture(exponent,'roughness') if exponent else None)
    if optic_glass:
        material = (ASSETS/'attachments/m4a1/optics/reflex_reticle.vmat').read_text()
        # The existing collimated lens shader supplies a functional aiming reticle.
        # Thermal/hybrid behaviour is separate from importing the physical lens.
    else:
        lines = ['Layer0','{',' shader "shaders/complex.shader"',' F_SPECULAR "1"',
                 ' g_vColorTint "[1 1 1 1]"',' g_flMetalness "0"']
        for field, role in [('TextureColor','color'),('TextureNormal','normal'),('TextureRoughness','roughness')]:
            if record[role]: lines.append(f' {field} "{record[role]}"')
        if not record['roughness']:
            roughness = min(.85,max(.18,(2/(vmt.get_float('$phongexponent',24)+2))**.25))
            lines.append(f' g_flRoughnessScaleFactor "{roughness:.4f}"')
        if glass or vmt.get_int('$translucent') or vmt.get_int('$alphatest'):
            lines.append(' F_TRANSLUCENT "1"' if not vmt.get_int('$alphatest') else ' F_ALPHA_TEST "1"')
            if color:
                record['opacity'] = texture(color,'opacity')
                lines.append(f' TextureTranslucency "{record["opacity"]}"')
        lines.append('}')
        material='\n'.join(lines)+'\n'
    destination=ASSETS/'attachments/mw2022/materials'/(full+'.vmat')
    destination.parent.mkdir(parents=True,exist_ok=True)
    destination.write_text(material,encoding='utf-8')
    record['vmat']=destination.relative_to(ASSETS).as_posix()
    return record


paths=set()
for file in (HERE/'models').glob('*.json'):
    paths.update(json.loads(file.read_text())['materials'].values())
for index,full in enumerate(sorted(paths)):
    try:
        materials[full]=convert(full)
    except Exception as exc:
        traceback.print_exc()
        failures.append(dict(material=full,error=str(exc)))
    print(f'MATERIAL {index+1}/{len(paths)} {full}',flush=True)
(HERE/'materials.json').write_text(json.dumps(dict(materials=materials,textures=list(texture_report.values()),notes=notes,failures=failures),indent=2)+'\n')
print('MATERIAL_SUMMARY',len(materials),'materials;',len(texture_report),'textures;',len(failures),'failures')
if failures:
    raise RuntimeError('Material conversion failed; see materials.json')
