"""Stage separate previews of the canonical photographed plaster materials."""
import json
from pathlib import Path

import belltower_quality_materials as M

ROOT = Path(__file__).resolve().parents[1]


def material_text(name, tint, coverage=.49):
    properties = M.scanned_plaster(tint, coverage)
    return '\n'.join([
        '// Photographed peeling render trial; original CC0 Poly Haven sources.',
        '"Layer0"', '{', '    shader "shaders/belltower_plaster.shader"',
        *[f'    {key} "{value}"' for key, value in properties.items() if key!='shader'], '}', '',
    ])


def main():
    output=ROOT/'output/belltower/quality/plaster-v1-materials.json'
    records=[{'path':f'materials/belltower/trials/plaster_{name}.vmat',
              'target':f'materials/belltower/plaster_{name}.vmat',
              'text':material_text(name,tint)} for name,tint in M.PAINTS.items()]
    output.write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
    print(f'Staged {len(records)} trial materials; accepted materials unchanged.')


if __name__=='__main__':
    main()
