"""Fit the complete reference-derived crown and preserve its projected surface detail."""
from pathlib import Path
import shutil
import sys
import numpy as np
import trimesh
import fast_simplification
from PIL import Image
from scipy.ndimage import distance_transform_edt, binary_closing, binary_fill_holes, gaussian_filter
from skimage.measure import marching_cubes

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'Assets/models/props/shared/veridant_fountain_reference_top_v2'
SOURCE = ROOT / 'Sources/Veridant/fountain-reference-top-v2'


def main(path):
    DEST.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, SOURCE / 'crown.glb')
    mesh = trimesh.load_mesh(path)
    mesh = max(mesh.split(only_watertight=False), key=lambda m: len(m.faces))
    low, high = mesh.bounds
    # Repair the reconstruction's thin perforated mane locks before decimation.
    # A sub-unit volumetric close creates solid cast-bronze forms without changing
    # the outer composition. Fine surface detail remains in the reference mapping.
    voxels = mesh.voxelized(pitch=.0085)
    solid = np.pad(voxels.matrix, 5)
    solid = binary_closing(solid, iterations=3)
    solid = binary_fill_holes(solid)
    verts, tris, _, _ = marching_cubes(gaussian_filter(solid.astype(float), .8), .5)
    verts = trimesh.transform_points(verts - 5, voxels.transform)
    mesh = trimesh.Trimesh(verts, tris)
    mesh.fix_normals()
    vertices, faces = fast_simplification.simplify(
        np.ascontiguousarray(mesh.vertices), np.ascontiguousarray(mesh.faces), target_count=220000)
    mesh = trimesh.Trimesh(vertices, faces, process=False)
    mesh.fix_normals()
    faces = mesh.faces
    im = Image.open(SOURCE / 'crown-source.png').convert('RGBA')
    rgba = np.array(im)
    mask = rgba[:, :, 3] > 215
    yy, xx = np.nonzero(mask)
    # Front projection matches the reconstruction's canonical image-facing axes.
    px = xx.min() + (vertices[:, 0] - low[0]) / (high[0] - low[0]) * (xx.max() - xx.min())
    py = yy.max() - (vertices[:, 1] - low[1]) / (high[1] - low[1]) * (yy.max() - yy.min())
    px = np.clip(px, 0, im.width - 1).astype(int)
    py = np.clip(py, 0, im.height - 1).astype(int)
    # Edge vertices sample actual sculpture texels instead of the transparent halo.
    _, nearest = distance_transform_edt(~mask, return_indices=True)
    missing = ~mask[py, px]
    py[missing], px[missing] = nearest[:, py[missing], px[missing]]
    uv = np.column_stack((px / im.width, 1 - py / im.height))
    # Explicit material boundary follows the isolated stone silhouette, avoiding
    # a brightness classifier that mistakes carved shadows for bronze.
    contour = np.array([(505,110),(600,75),(950,75),(1085,110),(1085,150),
        (1040,190),(990,230),(930,290),(880,360),(820,430),(775,510),
        (755,620),(735,720),(730,870),(745,885),(745,915),(583,915),
        (583,880),(610,870),(620,800),(620,720),(610,650),(600,570),
        (600,480),(610,400),(620,330),(620,270),(590,220),(550,195),(535,150)])
    cx = px[faces].mean(axis=1)
    cy = py[faces].mean(axis=1)
    stone_faces = np.zeros(len(faces), dtype=bool)
    for a, b in zip(contour, np.roll(contour, -1, axis=0)):
        if a[1] == b[1]:
            continue
        stone_faces ^= ((a[1] > cy) != (b[1] > cy)) & (cx < (b[0]-a[0])*(cy-a[1])/(b[1]-a[1])+a[0])
    # Include rounded moulding returns that project beyond the front panel edge.
    for a, b in zip(contour, np.roll(contour, -1, axis=0)):
        edge = b - a
        t = np.clip(((cx-a[0])*edge[0] + (cy-a[1])*edge[1]) / np.dot(edge, edge), 0, 1)
        stone_faces |= (cx-a[0]-t*edge[0])**2 + (cy-a[1]-t*edge[1])**2 < 30**2
    stone_faces |= (cy < 205) & (cx > 480) & (cx < 1110)
    stone_faces |= np.abs(vertices[faces, 0].mean(axis=1)) < .125
    scale = 68 / (high[0] - low[0])
    local = np.column_stack((vertices[:, 0] * scale,
                             vertices[:, 2] * scale,
                             48.55 + (vertices[:, 1] - low[1]) * scale))
    # Match the existing fountain's radial/lateral basis. OBJ is Y-up.
    basis = np.array(((.6, .8, 0), (-.8, .6, 0), (0, 0, 1)))
    points = local @ basis.T
    normal_local = np.column_stack((mesh.vertex_normals[:, 0], mesh.vertex_normals[:, 2], mesh.vertex_normals[:, 1]))
    normals = normal_local @ basis.T
    with (DEST / 'crown.obj').open('w') as out:
        out.write('mtllib crown.mtl\no reference_crown_v2\nusemtl crown_surface\n')
        for x, y, z in points:
            out.write(f'v {y:.6f} {z:.6f} {x:.6f}\n')
        for u, v in uv:
            out.write(f'vt {u:.7f} {v:.7f}\n')
        for x, y, z in normals:
            out.write(f'vn {y:.7f} {z:.7f} {x:.7f}\n')
        for stone in (False, True):
            out.write('usemtl ' + ('crown_stone' if stone else 'crown_surface') + '\n')
            for face in faces[stone_faces == stone, ::-1] + 1:
                out.write('f ' + ' '.join(f'{i}/{i}/{i}' for i in face) + '\n')
    (DEST / 'crown.mtl').write_text('newmtl crown_surface\nKd 0.2 0.2 0.2\nnewmtl crown_stone\nKd 0.5 0.5 0.5\n')
    template = (ROOT / 'Assets/models/props/shared/veridant_fountain_reference_top/crown.vmdl').read_text()
    template = template.replace('veridant_fountain_reference_top/crown.obj', 'veridant_fountain_reference_top_v2/crown.obj')
    template = template.replace('reference_bronze.vmat', 'crown_surface.vmat')
    template = template.replace('materials/veridant/fountain_reference_bronze.vmat', 'materials/veridant/fountain_reference_crown_v2.vmat')
    # The preceding name substitution also changes the target suffix.
    template = template.replace('materials/veridant/fountain_crown_surface.vmat', 'materials/veridant/fountain_reference_crown_v2.vmat')
    template = template.replace('carved_limestone.vmat', 'crown_stone.vmat').replace('materials/veridant/fountain_reference_limestone.vmat', 'materials/veridant/fountain_reference_crown_stone_v2.vmat')
    (DEST / 'crown.vmdl').write_text(template)
    shutil.copy2(SOURCE / 'crown-source.png', ROOT / 'Assets/materials/veridant/fountain_crown_v2_color.png')
    print('Faces', len(faces), 'Local bounds', local.min(axis=0), local.max(axis=0))


if __name__ == '__main__':
    main(sys.argv[1])
