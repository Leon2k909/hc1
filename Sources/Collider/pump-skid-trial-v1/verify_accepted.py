"""Verify the exact approved pump, isolated integration and retained collision offline."""
import os
for name in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '1'
import psutil
process = psutil.Process()
process.nice(psutil.IDLE_PRIORITY_CLASS)
process.cpu_affinity(process.cpu_affinity()[-2:])
from collections import Counter
from pathlib import Path
import ast, importlib.util, json, re, sys
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
sys.path.insert(0, str(ROOT / 'Tools'))
spec = importlib.util.spec_from_file_location('pump_install', HERE / 'install_accepted.py')
I = importlib.util.module_from_spec(spec)
spec.loader.exec_module(I)
import collider_pump_skid as PS
import collider_map as M
import map_kit as K


def attrs(path, local=False, selected_only=False, normalize_normals=False):
    positions, uv, normals, paint, result = [], [], [], '', Counter()
    active = not selected_only
    for line in path.read_text().splitlines():
        if line.startswith('v '):
            a, z, n = map(float, line.split()[1:])
            positions.append(np.array((-a, n, z)) + (PS.ORIGIN if local else 0))
        elif line.startswith('vt '):
            uv.append(tuple(map(float, line.split()[1:])))
        elif line.startswith('vn '):
            a, z, n = map(float, line.split()[1:])
            vector = np.array((-a, n, z))
            normals.append(K.normalise(vector) if normalize_normals else vector)
        elif line.startswith('usemtl '):
            paint = line[7:]
        elif line.startswith('o ') and selected_only:
            active = line.strip() == 'o collider_approved_pump_skid'
        elif line.startswith('f ') and active:
            ids = [[int(v) - 1 for v in t.split('/')] for t in line.split()[1:]]
            result[(paint, tuple(sorted(tuple(round(float(x), 6) for x in (*positions[v], *uv[t], *normals[n]))
                                       for v, t, n in ids)))] += 1
    return result


def model_attrs(model):
    result = Counter()
    for paint, polygons in model.polygons.items():
        for index, (points, normal) in enumerate(polygons):
            uv = model.polygon_uvs.get((paint, index), [(0., 0.)] * len(points))
            normals = model.polygon_normals.get((paint, index), [normal] * len(points))
            for k in range(1, len(points) - 1):
                result[(paint, tuple(sorted(tuple(round(float(x), 6) for x in (*points[j], *uv[j], *normals[j]))
                                           for j in (0, k, k + 1))))] += 1
    return result


def plain(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    return [plain(v) for v in value] if isinstance(value, (list, tuple)) else value


def placements():
    tree = ast.parse((ROOT / 'Tools/collider_map.py').read_text())
    node = next(n.iter for n in ast.walk(tree)
                if isinstance(n, ast.For) and isinstance(n.target, ast.Tuple)
                and [v.id for v in n.target.elts] == ['e', 'n', 'z', 'w', 'd', 'h', 'head'])
    class FloorConstant(ast.NodeTransformer):
        def visit_Name(self, n):
            assert n.id == 'G', n.id
            return ast.Constant(M.G)
        def visit_BinOp(self, n):
            n = self.generic_visit(n)
            assert isinstance(n.op, ast.Add)
            return ast.Constant(ast.literal_eval(n.left) + ast.literal_eval(n.right))
    return ast.literal_eval(FloorConstant().visit(node))


def main():
    d = json.loads((I.OUT / 'installed.json').read_text())
    rel = Path('models/maps/collider/collider_detail.obj')
    source = ROOT / 'Assets' / rel
    for record in d['files']:
        assert I.sha(ROOT / 'Assets' / record['relative']) == record['after'], record['relative']
    assert I.sha(ROOT / d['generatorFile']['path']) == d['generatorFile']['after']
    assert I.sha(ROOT / 'Tools/collider_pump_skid.py') == d['helperSHA256']
    for p, h in {**d['protectedOtherFiles'], **d['approvedProposalSources']}.items():
        assert I.sha(ROOT / p) == h, p
    old = (I.OUT / 'before' / rel).read_bytes().decode('utf-8').splitlines(keepends=True)
    removed = set(d['removedFaceLines'])
    assert len(removed) == 2420 and all(old[i - 1].startswith('f ') for i in removed)
    prefix = ''.join(line for i, line in enumerate(old, 1) if i not in removed).encode('utf-8')
    assert source.read_bytes().startswith(prefix)
    before = Counter(I.triangles(I.OUT / 'retired-before-resources/before.obj', local=True))
    after = Counter(I.triangles(I.TRIAL / 'after.obj', local=True))
    current = Counter(I.triangles(source))
    assert sum(before.values()) == 2420 and sum(after.values()) == 58005
    assert not before & current and all(current[key] == n for key, n in after.items())
    approved = attrs(I.TRIAL / 'after.obj', local=True)
    assert attrs(source, selected_only=True) == approved
    doc = source.with_suffix('.vmdl').read_bytes()
    old_doc = (I.OUT / 'before' / rel.with_suffix('.vmdl')).read_bytes()
    marker = b'PhysicsShapeList'
    assert old_doc[old_doc.index(marker):] == doc[doc.index(marker):]
    pattern = r'\{ from = "([^"]+)" to = "([^"]+)" \}'
    remaps = dict(re.findall(pattern, doc.decode()))
    old_remaps = dict(re.findall(pattern, old_doc.decode()))
    assert all(remaps[p] == path for p, path in old_remaps.items())
    assert all((ROOT / 'Assets' / p).is_file() for p in remaps.values())
    spec = importlib.util.spec_from_file_location('collider_before_pump', I.OUT / 'before/Tools/collider_map.py')
    previous = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(previous)
    approved_normalized = attrs(I.TRIAL / 'after.obj', local=True, normalize_normals=True)
    selected, other = 0, 0
    for args in placements():
        legacy, current_model = K.Model(), K.Model()
        previous.hardcase(legacy, *args)
        M.hardcase(current_model, *args)
        M.configure(current_model)
        assert plain(current_model.boxes) == plain(legacy.boxes)
        assert plain(current_model.hulls) == plain(legacy.hulls)
        if tuple(args) == (-850, -350, 0, 106, 58, 74, 0):
            selected += 1
            assert model_attrs(current_model) == approved_normalized
            for paint in current_model.polygons:
                assert current_model.material_overrides[paint] == remaps[paint + '.vmat']
        else:
            other += 1
            assert model_attrs(current_model) == model_attrs(legacy), args
    assert selected == 1
    assert all(not (ROOT / p).exists() for p in d['retiredOldStandaloneResources'])
    result = {
        'approvedPumpInstalled': True, 'approvedSurfaceRevision': 4, 'approvedTriangles': 58005,
        'oldCaseTrianglesRemaining': 0, 'exactApprovedPositionsUVsNormalsAndMaterials': True,
        'unrelatedOriginalFacesAndAttributesPreserved': True, 'fullPhysicsUnchanged': True,
        'generatorPreservesOriginalCollision': True, 'otherHardcasePlacementsUnchanged': other,
        'priorAcceptedPropsPreserved': True, 'sourceGeneratorMatchesExactly': True,
        'oldStandaloneResourcesArchivedOutsideAssets': True, 'editorUsed': False,
        'engineCompilation': 'pending', 'nativeAppearanceLODsAndPerformance': 'pending',
    }
    (I.OUT / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
