from pathlib import Path

root = Path(__file__).resolve().parents[3]
path = root / 'Tools/lowtide_container.py'
before = path.read_bytes()
newline = b'\r\n' if b'\r\n' in before else b'\n'
text = before.decode('utf-8').replace('\r\n', '\n')
assert 'import lowtide_container_surface as SURFACE' not in text
text = text.replace('import lowtide_container_detail as DETAIL\n',
                    'import lowtide_container_detail as DETAIL\nimport lowtide_container_surface as SURFACE\n', 1)
text = text.replace('def write_materials():\n    report = {}',
                    'def write_materials():\n    write_bytes(K.ASSETS / SURFACE.SHADER, SURFACE.SOURCE.read_bytes())\n    meta(K.ASSETS / SURFACE.SHADER)\n    report = {}', 1)
start = text.index('            normal_suffix = "frame_normal" if frame else "normal"\n')
end = text.index('            meta(OUT / f"{name}.vmat")', start)
text = text[:start] + '            K.write_text(OUT / f"{name}.vmat", SURFACE.material_text(colour, frame))\n' + text[end:]
data = text.encode('utf-8').replace(b'\n', newline)
assert path.read_bytes() == before
temporary = path.with_name(path.name + '.writing')
temporary.write_bytes(data)
temporary.replace(path)
print('Canonical container generator now emits the reviewed shader and six materials; texture calculations unchanged.')
