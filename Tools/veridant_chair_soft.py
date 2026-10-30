"""Walnut dining chair with sewn, shaped upholstery, in Source inches.

Render-only replacement at the original bistro-chair placements. Rounded timber
members carry the load; cushions sit on the rails and inside the back frame.
"""
import math

import numpy as np

import map_kit as K
import riverdale_parts as P
import veridant_lounger_soft as S


MATERIALS = {
    'vr_chair_cloth': 'materials/veridant/chair-v4/cloth.vmat',
    'vr_chair_piping': 'materials/veridant/chair-v4/piping.vmat',
    'vr_chair_walnut': 'materials/veridant/chair-v4/walnut.vmat',
    'vr_black': 'materials/veridant/vr_black.vmat',
    'vr_brass': 'materials/veridant/vr_brass.vmat',
}


def _wood(model, points, widths, depths, phase=0., paint='vr_chair_walnut'):
    """Parallel-transported, rounded rectangular timber with lengthwise UVs."""
    points = np.asarray(points, float)
    if np.isscalar(widths): widths = [widths]*len(points)
    if np.isscalar(depths): depths = [depths]*len(points)
    rings, shades, uvs, perimeters = [], [], [], []
    distances = np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    tangent = P.unit(points[1]-points[0])
    side = P.unit(np.cross(tangent, (0,0,1)))
    if np.linalg.norm(side)<.5: side = P.v(1,0,0)
    for i,(point,width,depth) in enumerate(zip(points,widths,depths)):
        tangent = P.unit(points[min(i+1,len(points)-1)]-points[max(i-1,0)])
        side = P.unit(side-tangent*np.dot(tangent,side))
        other = np.cross(tangent,side)
        end = i in (0,len(points)-1)
        w,h = np.array((width,depth))*.5-(.035 if end else 0.)
        radius = min(.16,w*.48,h*.48)
        ring, normals, uv = [], [], []
        for sx,sy,start in ((1,1,0),(-1,1,90),(-1,-1,180),(1,-1,270)):
            for angle in np.linspace(start,start+90,5):
                a = math.radians(angle)
                nx,ny = math.cos(a),math.sin(a)
                x,y = sx*(w-radius)+radius*nx,sy*(h-radius)+radius*ny
                ring.append(point+side*x+other*y)
                n = side*nx+other*ny
                if end: n += tangent*(-.22 if i==0 else .22)
                normals.append(P.unit(n))
        # Include the straight portions between corner arcs. Assigning only
        # corner angles collapses each flat face to a single texture column.
        arc_lengths=np.r_[0.,np.cumsum(np.linalg.norm(np.diff(np.asarray(ring),axis=0),axis=1))]
        perimeter=float(arc_lengths[-1]+np.linalg.norm(ring[-1]-ring[0]))
        uv=[(distance/7+phase*.173,distances[i]/36+phase*.23) for distance in arc_lengths]
        rings.append(ring); shades.append(normals); uvs.append(uv); perimeters.append(perimeter)
    count = len(rings[0])
    for i in range(len(points)-1):
        for j in range(count):
            k = (j+1)%count
            uv = [uvs[i][j],uvs[i][k],uvs[i+1][k],uvs[i+1][j]]
            if k==0:
                uv[1]=(uv[1][0]+perimeters[i]/7,uv[1][1])
                uv[2]=(uv[2][0]+perimeters[i+1]/7,uv[2][1])
            P.card(model,paint,[rings[i][j],rings[i][k],rings[i+1][k],rings[i+1][j]],
                   shades[i][j]+shades[i][k]+shades[i+1][j]+shades[i+1][k],
                   normals=[shades[i][j],shades[i][k],shades[i+1][k],shades[i+1][j]],uv=uv)
    for i,sign in ((0,-1),(-1,1)):
        toward = P.unit(points[1]-points[0])*-1 if i==0 else P.unit(points[-1]-points[-2])
        P.card(model,paint,rings[i],toward,
               uv=[((p[0]+phase)/8,(p[1]+phase)/8) for p in rings[i]])


def _cushion(model, centre, axes, length, width, thickness, phase):
    # Share the established cloth construction, but transform normals with the
    # inverse transpose when compressing it to a dining cushion's thickness.
    piece = K.Model()
    S.cushion(piece,(0,0,0),np.eye(3),length,width,phase)
    matrix = np.asarray(axes,float)
    matrix[2] *= thickness
    inverse = np.linalg.inv(matrix).T
    centre = np.asarray(centre,float)
    for paint,faces in piece.polygons.items():
        material = 'vr_chair_cloth' if paint=='vr_lounger_cloth' else 'vr_chair_piping'
        for i,(points,normal) in enumerate(faces):
            transformed = [centre+p@matrix for p in points]
            smooth = piece.polygon_normals.get((paint,i))
            P.card(model,material,transformed,P.unit(normal@inverse),
                   normals=[P.unit(n@inverse) for n in smooth] if smooth is not None else None,
                   uv=piece.polygon_uvs.get((paint,i)))


def build_into(model, at, facing, z0=0., paint='vr_wicker'):
    local = K.Model()
    phase = math.sin(float(at[0])*.071+float(at[1])*.043)*1.9

    def wood(points,widths,depths,offset=0.,material='vr_chair_walnut'):
        _wood(local,points,widths,depths,phase+offset,material)

    # The feet splay slightly. Timber tapers toward the glides and meets the
    # under-seat rails with substantial, rounded shoulders.
    for sign in (-1,1):
        wood([(6.65,sign*6.95,.14),(6.62,sign*6.92,.32),
              (6.40,sign*6.75,4.8),(6.14,sign*6.55,10.8),
              (5.95,sign*6.40,15.65),(5.95,sign*6.40,16.10)],
             [1.02,1.08,1.18,1.32,1.45,1.41],
             [1.04,1.10,1.20,1.34,1.48,1.44],sign)
        wood([(-7.55,sign*7.0,.14),(-7.52,sign*6.98,.32),
              (-7.10,sign*6.75,5.5),(-6.80,sign*6.55,11.5),
              (-6.90,sign*6.60,16.0),(-7.20,sign*7.13,19.0),
              (-7.66,sign*7.32,23.5),(-8.26,sign*7.35,28.0),
              (-8.95,sign*7.35,33.06)],
             [1.04,1.10,1.20,1.36,1.42,1.26,1.16,1.10,1.04],
             [1.08,1.14,1.24,1.40,1.46,1.30,1.22,1.16,1.10],sign+2)
        # Side apron and a low stretcher, with softly eased joinery edges.
        wood([(-6.85,sign*6.45,15.65),(-3.2,sign*6.46,15.67),
              (2.8,sign*6.45,15.65),(5.95,sign*6.40,15.65)],1.16,1.30,3+sign)
        wood([(-7.12,sign*6.76,5.8),(-2.5,sign*6.78,5.72),
              (2.9,sign*6.78,5.73),(6.36,sign*6.76,5.8)],.55,.63,5+sign)
        for x,y in ((6.65,sign*6.95),(-7.55,sign*7.0)):
            wood([(x,y,0),(x,y,.18)],1.01,1.03,0,'vr_black')

    for x in (-6.75,5.95):
        wood([(x,-6.4,15.65),(x,0,15.69),(x,6.4,15.65)],1.22,1.30,x)

    # Curved top and bottom rails follow the back's bow instead of making a
    # square board. Their ends enter the rear posts, like assembled furniture.
    for z,depth,width in ((32.55,1.08,1.04),(20.05,.90,.94)):
        points=[]
        for y in np.linspace(-7.35,7.35,11):
            x=-7.20-.132*(z-19.)+.0065*y*y
            points.append((x,y,z+.055*math.cos(y*.20)))
        wood(points,width,depth,z*.23)

    _cushion(local,(.0,0,17.14),np.eye(3),15.3,15.2,.42,phase)
    # Reclined upholstery leaves a reveal inside the timber surround. A small
    # lumbar bow is carried by the cushion's foam rather than a flat slab.
    u=P.unit((-0.132,0,1)); across=P.v(0,-1,0); outward=np.cross(u,across)
    _cushion(local,(-7.89,0,26.23),(u,across,outward),12.05,13.45,.25,phase+.8)

    f=P.unit(P.v(facing[0],facing[1],0)); s=np.cross((0,0,1),f)
    axes=np.array((f,s,(0,0,1))); origin=P.v(at[0],at[1],z0)
    for material,faces in local.polygons.items():
        for i,(points,normal) in enumerate(faces):
            smooth=local.polygon_normals.get((material,i))
            transformed=np.array([origin+p@axes for p in points])
            shading=[n@axes for n in smooth] if smooth is not None else None
            uv=local.polygon_uvs.get((material,i))
            # The OBJ writer stores milliinches. A few adaptive cloth samples
            # can coincide at that precision; omit only their zero-area faces.
            rounded=np.round(transformed,3)
            triangles=[(0,j,j+1) for j in range(1,len(points)-1)]
            valid=[tri for tri in triangles if np.linalg.norm(np.cross(
                rounded[tri[1]]-rounded[tri[0]],rounded[tri[2]]-rounded[tri[0]]))>1e-9]
            if len(valid)==len(triangles):
                P.card(model,material,transformed,normal@axes,normals=shading,uv=uv)
            else:
                for tri in valid:
                    P.card(model,material,[transformed[j] for j in tri],normal@axes,
                           normals=[shading[j] for j in tri] if shading is not None else None,
                           uv=[uv[j] for j in tri] if uv is not None else None)
    model.material_overrides.update(MATERIALS)
    model.tile_overrides.update({material:12. for material in MATERIALS})


def write_materials(directory):
    """Use the established woven cloth and walnut PBR textures, with own tints."""
    from pathlib import Path
    directory=Path(directory); directory.mkdir(parents=True,exist_ok=True)
    presets={
        'cloth':('lounger-v2/cloth',(.69,.60,.47),1.),
        'piping':('lounger-v2/cloth',(.53,.43,.31),1.05),
        'walnut':('backbar-v1/walnut',(.80,.89,1.05),1.15),
    }
    for name,(texture,tint,roughness) in presets.items():
        value=' '.join(str(v) for v in (*tint,1))
        (directory/(name+'.vmat')).write_text(
            '// Tools/veridant_chair_soft.py\n"Layer0"\n{\n'
            '    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n'
            '    g_flMetalness "0"\n'
            f'    g_flRoughnessScaleFactor "{roughness}"\n'
            f'    TextureColor "materials/veridant/{texture}_color.png"\n'
            f'    TextureNormal "materials/veridant/{texture}_normal.png"\n'
            f'    TextureRoughness "materials/veridant/{texture}_rough.png"\n'
            '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n'
            f'    g_vColorTint "[{value}]"\n    g_flModelTintAmount "1.0"\n}}\n',encoding='utf-8')
