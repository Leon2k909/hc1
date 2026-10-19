"""Preserve Lowtide's reviewed warehouse floor materials during map generation.

The colour atlas is copied unchanged. Normal/roughness maps are numerical surface
data. The concrete-use mask is an accepted static layout: restage it when cargo
or warehouse collision changes, before importing it through the native editor.
"""
import json
from pathlib import Path
import shutil
import uuid

import numpy as np
from PIL import Image

import map_kit as K
import lowtide_warehouse_floor as F
import lowtide_concrete_wear as C

MASK_SOURCE=K.ROOT/'Sources/Lowtide/concrete/warehouse-use.png'


def concrete_material(base):
    old='shader "shaders/hc1_lowtide_concrete.shader"'
    assert base.count(old)==1
    base=base.replace(old,f'shader "{C.SHADER}"',1)
    anchor='    g_flConcreteScale'
    assert base.count(anchor)==1
    return base.replace(anchor,f'    TextureWarehouseUse "{C.MASK}"\n    g_flWarehouseUse "1"\n'+anchor,1)


def write_materials(assets=None):
    assets=Path(assets) if assets is not None else K.ASSETS
    source=F.SOURCE/'warehouse-boards-source.png'
    rgb=np.asarray(Image.open(source).convert('RGB'),np.float32)/255
    bounds,rects=F.identify_rows(rgb)
    normal,rough,_=F.numerical_maps(rgb,bounds,rects)
    textures=assets/F.RESOURCE
    textures.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,textures/'warehouse_color.png')
    Image.fromarray(np.rint((normal*.5+.5)*255).clip(0,255).astype(np.uint8)).save(textures/'warehouse_normal.png')
    Image.fromarray(np.rint(rough*255).clip(0,255).astype(np.uint8)).save(textures/'warehouse_rough.png')
    F.write(assets/F.MATERIAL,F.material_text())
    F.write(assets/F.SHADER,(F.SOURCE/'warehouse-floor.shader').read_text())
    F.write(assets/'shaders/hc1_lowtide_floor_atlas.hlsl',F.atlas_text(rects))
    mask=assets/C.MASK
    mask.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(MASK_SOURCE,mask)
    F.write(assets/C.SHADER,C.staged_shader())
    F.write(assets/C.MATERIAL,concrete_material(C.BASE_MATERIAL.read_text()))
    resources=[F.MATERIAL,F.SHADER,'shaders/hc1_lowtide_floor_atlas.hlsl',
               *(f'{F.RESOURCE}/warehouse_{name}.png' for name in ('color','normal','rough')),
               C.MASK,C.MATERIAL,C.SHADER]
    for relative in resources:
        metadata=json.dumps({'guid':str(uuid.uuid5(uuid.NAMESPACE_URL,relative))},indent=2)+'\n'
        F.write(Path(str(assets/relative)+'.meta'),metadata)
    return resources


def configure(model):
    """Call only for the east/west warehouse architecture models."""
    if 'floorboards' not in model.polygons or 'rw_concrete' not in model.polygons:
        raise ValueError('Expected a Lowtide warehouse architecture model')
    model.material_overrides['floorboards']=F.MATERIAL
    model.material_overrides['rw_concrete']=C.MATERIAL
