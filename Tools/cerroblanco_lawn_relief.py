"""Stage subtle lawn crowning for review, without changing the live map."""
from pathlib import Path
import hashlib
import json
import math
import numpy as np
import cerroblanco_map as C
import map_kit as K

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'output/cerroblanco/lawn-relief-v1'
RESOURCE = 'models/maps/cerroblanco/lawn-relief-v1'
RISE = 4.0  # inches: 10.16 cm, rather than a new hill or obstacle


def height(e, n):
    x, y = abs(e - C.GARDEN[0]), abs(n - C.GARDEN[1])
    r = math.hypot(x, y)
    if r < 1e-6 or x <= 60 or y <= 60 or r >= 466:
        return 0.0
    if r <= 196:
        return 0.0
    def fade(distance):
        t = min(1.0, max(0.0, distance / 100.0))
        return t*t*(3-2*t)
    # Fixed-width edge fades avoid a ridge where a straight path meets a curved lawn edge.
    return RISE * math.sin(math.pi * (r-196)/270) ** 2 * fade(x-60) * fade(y-60)


def normal(e, n):
    d = 0.1
    return (-(height(e+d, n)-height(e-d, n))/(2*d),
            -(height(e, n+d)-height(e, n-d))/(2*d), 1)


def main():
    source = ROOT / 'Assets/scenes/maps/CerroBlanco/cerroblanco.scene'
    baseline = hashlib.sha256(source.read_bytes()).hexdigest()
    original = K.Model()
    for a in (0, 90, 180, 270):
        C.lawn_quarter(original, C.GARDEN, a)
    model = K.Model()
    max_slope, max_rise = 0.0, 0.0
    for points, _ in original.polygons[C.LAWN]:
        if len(points) == 3:
            # The narrow tips collapse to triangles and stay at their original edge height.
            top = [p + np.array((0,0,0.015)) for p in points]
            model.polygon(C.LAWN, top)
            continue
        assert len(points) == 4
        a, b, c, d = points
        # Subdivide radially; original angular boundaries and all kerbs remain in place.
        for j in range(16):
            t0, t1 = j/16, (j+1)/16
            pts = [a+(b-a)*t0, a+(b-a)*t1, d+(c-d)*t1, d+(c-d)*t0]
            raised = [np.array((p[0], p[1], p[2]+height(p[0],p[1])+0.015)) for p in pts]
            max_rise = max(max_rise, *(height(p[0],p[1]) for p in pts))
            for ids in ((0,1,2), (0,2,3)):
                top = [raised[i] for i in ids]
                face = np.cross(top[1]-top[0], top[2]-top[0])
                if np.linalg.norm(face) < 1e-8:
                    continue
                assert face[2] > 0
                max_slope = max(max_slope, math.degrees(math.atan2(np.linalg.norm(face[:2]),face[2])))
                model.polygon(C.LAWN, top, normals=[normal(p[0],p[1]) for p in top])
    model.material_overrides[C.LAWN] = 'materials/buildings/lawn.vmat'
    # Keep the original grounds UV phase so the new surface uses the same grass alignment.
    model.uv_source_name = 'cerroblanco_grounds'
    print('Surface measurements:', max_rise, max_slope)
    assert max_rise <= 4.001 and max_slope < 8
    for a in np.linspace(0, 2*math.pi, 361):
        for r in (196,466):
            assert abs(height(C.GARDEN[0]+r*math.cos(a),C.GARDEN[1]+r*math.sin(a))) < 1e-8
    dest = OUT / 'stage' / RESOURCE
    K.write_model(dest, RESOURCE, 'garden_lawn_relief', model)
    vmdl = dest / 'garden_lawn_relief.vmdl'
    text = vmdl.read_text()
    marker = '\t\tchildren =\n\t\t[\n'
    physics = '''
            {
                _class = "PhysicsShapeList"
                children = [
                    {
                        _class = "PhysicsMeshFile"
                        name = "lawn_surface"
                        parent_bone = ""
                        surface_prop = "grass"
                        collision_tags = "solid"
                        recenter_on_parent_bone = false
                        offset_origin = [ 0, 0, 0 ]
                        offset_angles = [ 0, 0, 0 ]
                        align_origin_x_type = "None"
                        align_origin_y_type = "None"
                        align_origin_z_type = "None"
                        filename = "models/maps/cerroblanco/lawn-relief-v1/garden_lawn_relief.obj"
                        import_scale = 1.0
                        maxMeshVertices = 0
                        qemError = 0.0
                        import_filter = { exclude_by_default = false exception_list = [ ] }
                    },
                ]
            },
'''
    assert marker in text
    vmdl.write_text(text.replace(marker,marker+physics,1))
    receipt = {'state':'staged review only, not installed', 'scene_sha256':baseline,
               'maximum_rise_inches':max_rise, 'maximum_rise_cm':max_rise*2.54,
               'maximum_triangle_slope_degrees':max_slope, 'render_triangles':model.triangle_count(),
               'collision_meshes':1, 'model':RESOURCE+'/garden_lawn_relief.vmdl',
               'placement_world':[0,0,0], 'editor_used':False,
               'checks':['inner and outer edges unchanged','rise at most 4 inches','slope below 8 degrees']}
    assert hashlib.sha256(source.read_bytes()).hexdigest()==baseline
    (OUT/'validation.json').write_text(json.dumps(receipt,indent=2))
    print(json.dumps(receipt,indent=2))


if __name__=='__main__':
    main()
