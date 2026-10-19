"""Offline staging for roughness-aware Lowtide planar reflection filtering.

The live capture allocates one mip and the shader always samples level zero.
This candidate adds a bounded linear-HDR mip chain and selects it by projected
roughness and UV footprint. It preserves the existing capture/view lifecycle,
waves, refraction/absorption, reflection projection, lighting and blending.
"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import uuid
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/lowtide/quality-pass/water-filter'
SOURCE = ROOT/'Sources/Lowtide/water'
ENGINE = Path('D:/SteamLibrary/steamapps/common/sbox')
CODE = 'Code/Map/LowtideWaterReflections.cs'
BASE_SHADER = 'Assets/shaders/hc1_lowtide_water.shader'
SHADER = 'Assets/shaders/hc1_lowtide_water_filtered.shader'
MATERIAL = 'Assets/materials/lowtide/lt_water.vmat'
MAX_MIPS = 7


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')


def code():
    original = (ROOT/CODE).read_text()
    allocation = '            var target = commands.GetRenderTarget( "lowtide-reflection", width, height,'
    added = (f'            // A short linear-HDR pyramid supplies roughness and minification filtering.\n'
             f'            var reflectionMips = 1;\n'
             f'            for ( var extent = Math.Min( width, height ); extent > 1 && reflectionMips < {MAX_MIPS}; extent >>= 1 )\n'
             f'                reflectionMips++;\n')
    count = 'ImageFormat.RGBA16161616F, ImageFormat.D24S8, MultisampleAmount.MultisampleNone, 1 );'
    replacement = count.replace(', 1 );', ', reflectionMips );')
    publish = '            // Published after the nested view completes. DrawReflection guards'
    filtering = ('            // Generate only after the reflected view is complete, before publishing its texture.\n'
                 '            // Box filtering preserves linear HDR radiance; the engine Gaussian path applies a display-space transform.\n'
                 '            if ( reflectionMips > 1 )\n'
                 '                commands.GenerateMipMaps( target, Sandbox.Graphics.DownsampleMethod.Box );\n')
    for anchor in (allocation, count, publish):
        assert original.count(anchor) == 1, anchor
    candidate = original.replace(allocation, added+allocation, 1).replace(count, replacement, 1).replace(publish, filtering+publish, 1)
    assert candidate.replace(added, '', 1).replace(replacement, count, 1).replace(filtering, '', 1) == original
    return candidate


def shader():
    original = (ROOT/BASE_SHADER).read_text()
    declaration = (SOURCE/'reflection-filter.hlsl').read_text()
    anchor = '    float4 MainPs( PixelInput input ) : SV_Target0'
    sample = 'g_tWaterReflection.SampleLevel( WaterReflectionSampler, saturate( uv ), 0 ).rgb'
    replacement = 'FilteredPlanarReflection( saturate( uv ), water.Roughness )'
    assert original.count(anchor) == original.count(sample) == 1
    candidate = original.replace(anchor, declaration+'\n'+anchor, 1).replace(sample, replacement, 1)
    assert candidate.replace(declaration+'\n', '', 1).replace(replacement, sample, 1) == original
    return candidate


def mip_dimensions(width, height):
    result = [(width, height)]
    while min(width, height) > 1 and len(result) < MAX_MIPS:
        width, height = max(1, width//2), max(1, height//2)
        result.append((width, height))
    return result


def api_evidence():
    xml = ENGINE/'bin/managed/Sandbox.Engine.xml'
    names = [
        'M:Sandbox.Rendering.CommandList.GenerateMipMaps(Sandbox.Rendering.RenderTargetHandle,Sandbox.Graphics.DownsampleMethod)',
        'M:Sandbox.Rendering.CommandList.GetRenderTarget(System.String,System.Int32,System.Int32,Sandbox.ImageFormat,Sandbox.ImageFormat,Sandbox.MultisampleAmount,System.Int32)',
        'F:Sandbox.Graphics.DownsampleMethod.Box',
    ]
    members = {m.attrib['name']:m for m in ET.parse(xml).findall('.//member')}
    assert all(name in members for name in names)
    downsample = ENGINE/'core/shaders/downsample_cs.shader'
    text = downsample.read_text()
    assert 'float3 FilterBilinear' in text and 'return D_DOWNSAMPLE_METHOD == DownsampleMethod::GaussianBlur' in text
    return dict(installed_api={name:' '.join(' '.join(members[name].itertext()).split()) for name in names},
                external_sources={p.as_posix():sha(p) for p in (xml, downsample, ENGINE/'bin/managed/Sandbox.Engine.dll', ENGINE/'bin/managed/Sandbox.System.dll')},
                filter='Native Box path averages four nonnegative linear HDR samples; Gaussian path converts to display space.')


def compile_project(out):
    folder = out/'compile'
    folder.mkdir(parents=True, exist_ok=True)
    references = '\n'.join(f'    <Reference Include="{name}"><HintPath>{escape((ENGINE/"bin/managed"/(name+".dll")).as_posix())}</HintPath><Private>false</Private></Reference>'
                           for name in ('Sandbox.System', 'Sandbox.Engine', 'Sandbox.Filesystem', 'Sandbox.Reflection', 'Sandbox.Mounting'))
    project = f'''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <TargetFramework>net10.0</TargetFramework>
    <AssemblyName>LowtideWaterOfflineCheck</AssemblyName>
    <LangVersion>14</LangVersion>
    <EnableDefaultCompileItems>false</EnableDefaultCompileItems>
    <Nullable>disable</Nullable>
    <UseSharedCompilation>false</UseSharedCompilation>
    <GenerateAssemblyInfo>false</GenerateAssemblyInfo>
    <NuGetAudit>false</NuGetAudit>
  </PropertyGroup>
  <ItemGroup>
    <Compile Include="../stage/{CODE}" />
    <Using Include="System" />
    <Using Include="System.Collections.Generic" />
    <Using Include="System.Linq" />
    <Using Include="Sandbox" />
    <Using Include="Sandbox.Internal.GlobalGameNamespace" Static="true" />
{references}
  </ItemGroup>
</Project>
'''
    write(folder/'WaterCheck.csproj', project)
    write(folder/'NuGet.Config', '<configuration><packageSources><clear /></packageSources></configuration>\n')


def build(out=OUT):
    out = out.resolve()
    assert out.is_relative_to(ROOT/'output/lowtide/quality-pass')
    previous = json.loads((ROOT/'output/lowtide/quality-pass/paving-use/manifest.json').read_text())
    protected = dict(previous['protected'])
    for rel in (CODE, BASE_SHADER, MATERIAL, 'Tools/lowtide_water.py'):
        protected[rel] = sha(ROOT/rel)
    assert all(sha(ROOT/p) == h for p, h in protected.items())
    api = api_evidence()
    stage = out/'stage'
    write(stage/CODE, code())
    write(stage/SHADER, shader())
    original = (ROOT/MATERIAL).read_text()
    old = 'shader "shaders/hc1_lowtide_water.shader"'
    assert original.count(old) == 1
    material = original.replace(old, 'shader "shaders/hc1_lowtide_water_filtered.shader"\n    g_flReflectionFilter "1"', 1)
    write(stage/MATERIAL, material)
    write(Path(str(stage/SHADER)+'.meta'), json.dumps(dict(guid=str(uuid.uuid5(uuid.NAMESPACE_URL, SHADER[7:]))), indent=2)+'\n')
    compile_project(out)
    patch = ''.join(difflib.unified_diff((ROOT/CODE).read_text().splitlines(True), code().splitlines(True), fromfile=CODE, tofile=CODE))
    write(out/'capture-change.diff', patch)
    sources = {p.relative_to(ROOT).as_posix():sha(p) for p in (Path(__file__), SOURCE/'reflection-filter.hlsl', ROOT/CODE, ROOT/BASE_SHADER, ROOT/MATERIAL)}
    staged = {p.relative_to(stage).as_posix():sha(p) for p in sorted(stage.rglob('*')) if p.is_file()}
    before = {p:(sha(ROOT/p) if (ROOT/p).is_file() else None) for p in staged}
    targets = []
    for width, height in ((256, 144), (640, 360), (960, 540), (1280, 720), (256, 1)):
        dims = mip_dimensions(width, height)
        extra = sum(w*h*8 for w, h in dims[1:])
        targets.append(dict(size=[width, height], mips=dims, additional_color_bytes=extra,
                            additional_color_fraction=extra/(width*height*8), extra_mip_passes=len(dims)-1))
    manifest = dict(revision='linear-hdr-planar-filter-v1', status='offline_candidate_not_installed',
                    production_changed=False, code_changed=False, native_accepted=False, canonical_generator_changed=False,
                    sources=sources, protected=protected, api=api, staged_files=staged, live_before=before,
                    unchanged=['capture registration and release lifecycle', 'view recursion and camera guards',
                               'water exclusion, projection and flip', 'waves, absorption, transparency, lighting and fog',
                               'scene, geometry, collision and source artwork'],
                    max_mips=MAX_MIPS, target_costs=targets, extra_water_texture_lookups=0,
                    limitations=['Mip filtering is an approximate projected roughness footprint, not a full GGX convolution',
                                 'Native shader compilation, sandbox hotload, GPU barriers/lifecycle, temporal appearance and performance unverified'])
    assert all(sha(ROOT/p) == h for p, h in protected.items())
    write(out/'manifest.json', json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(dict(stage=str(stage), files=len(staged), protected=len(protected),
                         max_mips=MAX_MIPS, additional_960x540_color_bytes=targets[2]['additional_color_bytes']), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUT)
    build(parser.parse_args().output)
