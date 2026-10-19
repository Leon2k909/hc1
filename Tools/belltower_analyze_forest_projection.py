"""Estimate forest-card minification from saved native cameras and current crowns."""
import hashlib
import json
import math
from pathlib import Path
import re

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output/belltower/quality/forest-coverage-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quantiles(values):
    return dict(zip(('p05', 'p25', 'p50', 'p75', 'p95'), map(float, np.quantile(values, [.05, .25, .5, .75, .95])))) if len(values) else None


def project(crowns, metadata, atlas):
    camera = metadata['Capture']
    assert metadata['Projection']['FovAxis'] == 'Horizontal'
    width, height = metadata['Projection']['Width'], metadata['Projection']['Height']
    eye = np.array(list(map(float, camera['Position'].split(','))))
    pitch, yaw, roll = map(math.radians, map(float, re.findall(r'=\s*([-0-9.]+)', camera['Angles'])))
    assert abs(roll) < 1e-6
    forward = np.array((math.cos(pitch)*math.cos(yaw), math.cos(pitch)*math.sin(yaw), -math.sin(pitch)))
    right = np.cross(forward, (0, 0, 1))
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    e, n, ground, radius, mid, half = crowns[:, :6].T
    heading = np.arctan2(n - 167, e) + math.pi/2
    de, dn = np.cos(heading)*radius, np.sin(heading)*radius
    tall = mid + half
    center = np.column_stack((n, -e, ground + tall*(.5-.025)))
    du = np.column_stack((2*dn, -2*de, np.zeros(len(e))))
    dv = np.column_stack((np.zeros(len(e)), np.zeros(len(e)), tall))
    delta = center - eye
    z, x, y = delta @ forward, delta @ right, delta @ up
    focal = width / (2 * math.tan(math.radians(camera['FieldOfView'])/2))
    safe_z = np.maximum(z, 1)
    sx, sy = width/2 + focal*x/safe_z, height/2 - focal*y/safe_z
    j11 = focal*((du @ right)*safe_z - x*(du @ forward))/safe_z**2
    j21 = -focal*((du @ up)*safe_z - y*(du @ forward))/safe_z**2
    j12 = focal*((dv @ right)*safe_z - x*(dv @ forward))/safe_z**2
    j22 = -focal*((dv @ up)*safe_z - y*(dv @ forward))/safe_z**2
    determinant = j11*j22 - j12*j21
    valid = (z > 1) & (sx >= 0) & (sx < width) & (sy >= 0) & (sy < height) & (np.abs(determinant) > 1e-8)
    variants = np.where(crowns[:, 6] == 8, 1, np.where(crowns[:, 11] % 3 < 1, 0, 3))
    rect_widths = np.array((.547, .441, .547, .441))[variants] * atlas['TextureWidth']
    rect_heights = np.array((.528, .528, .441, .441))[variants] * atlas['TextureHeight']
    inverse_det = np.zeros_like(determinant)
    inverse_det[valid] = 1/determinant[valid]
    dx_u, dx_v = rect_widths*j22*inverse_det, -rect_heights*j21*inverse_det
    dy_u, dy_v = -rect_widths*j12*inverse_det, rect_heights*j11*inverse_det
    mip = np.maximum(0, .5*np.log2(np.maximum(np.maximum(dx_u**2+dx_v**2, dy_u**2+dy_v**2), 1e-8)))
    pixel_width, pixel_height = np.hypot(j11, j21), np.hypot(j12, j22)
    distance = np.linalg.norm(delta, axis=1)
    near_boundary = valid & (distance >= 21000) & (distance <= 23000)
    return dict(frustum_center_count=int(valid.sum()), projected_width_pixels=quantiles(pixel_width[valid]),
                projected_height_pixels=quantiles(pixel_height[valid]), source_atlas_lod=quantiles(mip[valid]),
                fraction_width_below_4px=float(np.mean(pixel_width[valid] < 4)),
                fraction_lod_at_least_6=float(np.mean(mip[valid] >= 6)),
                fraction_at_or_beyond_last_native_mip=float(np.mean(mip[valid] >= atlas['TextureMipCount']-1)),
                tested_22k_boundary=dict(count=int(near_boundary.sum()), projected_width_pixels=quantiles(pixel_width[near_boundary]),
                                          source_atlas_lod=quantiles(mip[near_boundary])))


def main():
    path = ROOT / 'output/belltower/quality/parcel-v4-forest/crowns.npy'
    crowns = np.load(path, mmap_mode='r')
    assert crowns.shape == (320000, 12) and np.isfinite(crowns).all()
    atlas_path = OUT / 'native-atlas-metadata.json'
    atlas = json.loads(atlas_path.read_text())
    assert atlas['GamePreserved'] and atlas['SelectedDocumentPreserved'] and atlas['AssetsWritten'] == 0
    assert atlas['TextureWidth'] == atlas['TextureHeight'] == 1254 and atlas['TextureMipCount'] == 9
    results = []
    for view in ('west-ridge', 'west-ridge-detail', 'valley', 'terrace'):
        capture = ROOT / f'output/belltower/quality/forest-detail-v1-native-baseline-current/{view}-camera.json'
        metadata = json.loads(capture.read_text())
        assert metadata['SourceSceneSha256'] == sha(ROOT / 'Assets/scenes/maps/Belltower/belltower.scene')
        results.append(dict(view=view, camera_metadata_sha256=sha(capture), **project(crowns, metadata, atlas)))
    report = dict(scope='Analytical projection at card centres, without terrain or building occlusion. Counts are not native visible-tree counts. Source atlas dimensions and rounded saved camera angles are used.',
                  crowns_sha256=sha(path), analyzer_sha256=sha(Path(__file__)), native_atlas_metadata_sha256=sha(atlas_path), views=results,
                  texture_inputs_changed=False, geometry_changed=False, native_coverage_verified=False)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'projection-analysis.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps([dict(view=v['view'], frustum_centres=v['frustum_center_count'], width_median=v['projected_width_pixels']['p50'],
                           lod_median=v['source_atlas_lod']['p50'], below_4px=v['fraction_width_below_4px'],
                           boundary_width=v['tested_22k_boundary']['projected_width_pixels']) for v in results]))


if __name__ == '__main__':
    main()
