"""Splice this session's Railhead changes into the installed models as they are on disk, keeping other sessions' edits.

Other sessions are editing the generator and splicing their own changes into the same OBJs, so the map isn't rebuilt.
Instead the affected models are built twice from one snapshot of the code, in two processes started together:
"new" (the code as it is) and "old" (this session's changes switched back to what they replaced, by patching the
functions at run time). The faces only "old" has are this change's removals, the faces only "new" has its additions.

    python splice.py build old OUT      (and, at the same time, python splice.py build new OUT)
    python splice.py stage              compare the two builds' module hashes, splice into stage/, write publish.json

stage refuses if the two builds didn't load identical code, or if any face to remove isn't in the installed OBJ. It
drops the removed faces' lines and appends the added faces (with their own v/vt/vn) under their usemtl; every other
line of the installed OBJ stays. A .mtl or .vmdl is replaced only if the installed one is exactly "old"'s.
"""
import hashlib
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path( __file__ ).resolve().parent
ROOT = HERE.parents[2]
TOOLS = ROOT / "Tools"
INSTALLED = ROOT / "Assets/models/maps/railhead"
MODELS = ( "railhead_east", "railhead_west", "railhead_track", "railhead_dress_east", "railhead_dress_west",
           "railhead_dress_centre", "railhead_dress_glass" )
# The installed files each model's OBJ and MTL are in, relative to INSTALLED. Since the extinguisher-v2 import
# (2026-10-25 05:02) the dressing halves render extinguisher-v2/<side>-base.obj (beside its own extinguisher mesh), and
# railhead_dress_<side>.obj is the same base with the extinguishers in it: both get the change.
COPIES = { "railhead_dress_east": ( "extinguisher-v2/east-base", "railhead_dress_east" ),
           "railhead_dress_west": ( "extinguisher-v2/west-base", "railhead_dress_west" ) }
MTL_COPIES = { "railhead_dress_east": ( "extinguisher-v2/railhead_dress_east", "railhead_dress_east" ),
               "railhead_dress_west": ( "extinguisher-v2/railhead_dress_west", "railhead_dress_west" ) }


def sha( path ):
    return hashlib.sha256( Path( path ).read_bytes() ).hexdigest()


# ---------------------------------------------------------------------------------------------------------------------
# Building

def eager_imports():
    """ Every Tools module the railhead scripts import, loaded now, so the whole build uses one snapshot. """
    sys.path.insert( 0, str( TOOLS ) )
    names = set()
    for path in TOOLS.glob( "railhead_*.py" ):
        names.add( path.stem )
        for match in re.finditer( r"^\s*(?:import|from)\s+([A-Za-z_][A-Za-z0-9_]*)", path.read_text( encoding="utf-8" ), re.M ):
            names.add( match.group( 1 ) )
    # Scripts that do their work at import (a 2026-10-25 run padded Assets' rotunda_impostor.png through
    # railhead_rotunda_padding), and other sessions' staging scripts: never imported here.
    scripts = { "railhead_rotunda_padding", "railhead_civic_asset", "railhead_rotunda_bake", "railhead_render" }
    names = { n for n in names if n not in scripts and not n.startswith( "railhead_stage_" ) }
    loaded = {}
    for name in sorted( names ):
        if ( TOOLS / f"{name}.py" ).exists():
            try:
                __import__( name )
            except Exception as error:
                print( f"  {name}: {type( error ).__name__}: {error}" )
    for name, module in list( sys.modules.items() ):
        f = getattr( module, "__file__", None )
        if f and Path( f ).resolve().parent == TOOLS:
            loaded[name] = sha( f )
    return loaded


def switch_back():
    """ This session's changes, switched back to what they replaced. """
    import numpy as np
    import railhead_buffer as B
    import railhead_map as RMAP
    import railhead_props as P
    import railhead_station as S

    def old_bevel_box( model, frame, lo, hi, paint, bevel=0.15, edge=None, face_uv=False ):
        from railhead_props import outward
        lo, hi = np.asarray( lo, float ), np.asarray( hi, float )
        b = min( bevel, float( np.min( hi - lo ) ) * 0.45 )
        centre = ( lo + hi ) / 2
        half = ( hi - lo ) / 2
        axes = ( frame.x, frame.y, frame.z )

        def draw( points, normal, material, uv=False ):
            coords = None
            if uv:
                coords = [ ( ( q[0] - lo[0] ) / ( hi[0] - lo[0] ), ( q[2] - lo[2] ) / ( hi[2] - lo[2] ) ) for q in points ]
            outward( model, material, [ frame.p( *q ) for q in points ], sum( axes[i] * normal[i] for i in range( 3 ) ),
                     uv=coords )

        for i in range( 3 ):
            j, k = ( i + 1 ) % 3, ( i + 2 ) % 3
            for sign in ( -1, 1 ):
                points = []
                for sj, sk in ( ( -1, -1 ), ( 1, -1 ), ( 1, 1 ), ( -1, 1 ) ):
                    q = centre.copy()
                    q[i] += sign * half[i]
                    q[j] += sj * ( half[j] - b )
                    q[k] += sk * ( half[k] - b )
                    points.append( q )
                normal = np.zeros( 3 )
                normal[i] = sign
                draw( points, normal, paint, face_uv and i == 1 )
        for i, j, k in ( ( 0, 1, 2 ), ( 0, 2, 1 ), ( 1, 2, 0 ) ):
            for si in ( -1, 1 ):
                for sj in ( -1, 1 ):
                    points = []
                    for sk, inset in ( ( -1, i ), ( 1, i ), ( 1, j ), ( -1, j ) ):
                        q = centre.copy()
                        q[i] += si * half[i]
                        q[j] += sj * half[j]
                        q[k] += sk * ( half[k] - b )
                        q[inset] -= ( si if inset == i else sj ) * b
                        points.append( q )
                    normal = np.zeros( 3 )
                    normal[i], normal[j] = si, sj
                    draw( points, normal, edge or paint )
        for sx in ( -1, 1 ):
            for sy in ( -1, 1 ):
                for sz in ( -1, 1 ):
                    signs = np.array( ( sx, sy, sz ) )
                    corner = centre + signs * half
                    points = [ corner - np.eye( 3 )[i] * signs[i] * b for i in range( 3 ) ]
                    draw( points, signs, edge or paint )

    B.bevel_box = old_bevel_box
    for name in ( "railhead_luggage", "railhead_signal_frame" ):
        if name in sys.modules and hasattr( sys.modules[name], "bevel_box" ):
            sys.modules[name].bevel_box = old_bevel_box

    def old_bench( model, e, n, z0=0.0, facing="+e", length=78.7, slats="rw_wood", frame=P.DARK ):
        F = P.frame_for( e, n, z0, facing )
        model.grain_paints.add( slats )
        c, hl = 2.55, length / 2
        width = ( 16.5 - 3 * 0.5 ) / 4
        for k in range( 4 ):
            y0 = -8.0 + c + k * ( width + 0.5 )
            try:
                import railhead_buffer as B_
                B_.bevel_box( model, F, ( -hl, y0, P.BENCH_SEAT - 1.3 ), ( hl, y0 + width, P.BENCH_SEAT ), slats, 0.55 )
            except Exception:
                F.box( model, -hl, hl, y0, y0 + width, P.BENCH_SEAT - 1.3, P.BENCH_SEAT, slats )
        t = math.radians( 14.0 )
        up, nrm = np.array( ( 0.0, -math.sin( t ), math.cos( t ) ) ), np.array( ( 0.0, math.cos( t ), math.sin( t ) ) )
        base = np.array( ( 0.0, -8.6 + c, 19.0 ) )
        for k in range( 3 ):
            centre = base + up * ( 1.75 + k * 4.05 ) - nrm * 0.6
            P._obox( model, F, centre, ( 1, 0, 0 ), nrm, ( length, 1.2, 3.5 ), slats )
        posts = [ -hl + 7.0, hl - 7.0 ] + ( [ 0.0 ] if length > 70.0 else [] )
        back0, back1 = base - nrm * 2.0 - up * 3.0, base - nrm * 2.0 + up * 11.0
        try:
            import railhead_furniture as FU
            cast = FU.bench_frames
        except Exception:
            cast = None
        for x in ( posts if cast is None else () ):
            P._fbeam( model, F, ( x, 6.8 + c, 0.0 ), ( x, 6.8 + c, P.BENCH_SEAT - 1.3 ), ( 1.6, 1.6 ), frame )
            P._fbeam( model, F, ( x, back0[1] + 0.4, P.BENCH_SEAT - 2.1 ), ( x, 8.4 + c, P.BENCH_SEAT - 2.1 ), ( 1.4, 1.6 ),
                      frame )
            P._fbeam( model, F, ( x, -8.4 + c, 0.0 ), ( x, back0[1], back0[2] ), ( 1.6, 1.6 ), frame )
            P._fbeam( model, F, ( x, back0[1], back0[2] ), ( x, back1[1], back1[2] ), ( 1.6, 1.6 ), frame )
        try:
            import railhead_furniture as FU
            if cast is not None:
                cast( model, F, posts, c, P.BENCH_SEAT, frame, ( back0[1], back0[2] ), ( back1[1], back1[2] ) )
            FU.bench_details( model, F, posts, c, P.BENCH_SEAT, frame )
        except Exception as error:
            print( f"railhead_furniture.bench_details failed: {error}" )
        F.collide( model, -hl, hl, -9.4 + c, 8.5 + c, 0.0, P.BENCH_SEAT, "wood" )
        F.collide( model, -hl, hl, back1[1] - 0.8, -9.4 + c, 0.0, back1[2] + 1.0, "wood" )

    P.bench = old_bench
    RMAP.ROAD_VEHICLES_ENABLED = True
    detail = RMAP.detail

    def old_detail( name, *args, **kw ):
        if name == "notice_board" and kw.get( "size" ) == ( 11.7, 16.5 ):
            kw = dict( kw )
            del kw["size"]
            kw["bottom"] = S.DECK_Z + 22.0
        return detail( name, *args, **kw )

    RMAP.detail = old_detail
    luminaire = S.luminaire
    old_canopy_n = { -1656.0: -1626.0, -1570.0: None, -1484.0: -1506.0, -1382.0: -1386.0 }

    def old_luminaire( model, c, along, *args, **kw ):
        e, n, z = ( float( v ) for v in c )
        if along == "n" and abs( z - ( S.BRIDGE_ROOF - 4.0 ) ) < 1e-6:
            z = S.BRIDGE_ROOF
        elif along == "n" and n in old_canopy_n and z in ( S.CANOPY_Z, S.CANOPY_Z - 4.0 ):
            if old_canopy_n[n] is None:
                return
            n, z = old_canopy_n[n], S.CANOPY_Z
        return luminaire( model, ( e, n, z ), along, *args, **kw )

    S.luminaire = old_luminaire


def build( variant, out ):
    out = Path( out )
    loaded = eager_imports()
    import map_kit as K
    import railhead_buffer
    import railhead_map as RMAP
    import railhead_station as S
    if variant == "old":
        switch_back()
    models = dict( S.build() )
    models["railhead_track"] = RMAP.track_model()
    railhead_buffer.ballast_detail( models["railhead_track"] )
    east, west, centre = RMAP.dress_side( 1 ), RMAP.dress_side( -1 ), RMAP.dress_centre()
    glass = K.Model()
    for m in ( east, west, centre ):
        glass.extend( RMAP.split_paints( m, RMAP.GLASS_PAINTS ) )
    models["railhead_dress_east"], models["railhead_dress_west"] = east, west
    models["railhead_dress_centre"], models["railhead_dress_glass"] = centre, glass
    target = out / "models/maps/railhead"
    for name in MODELS:
        RMAP.configure( models[name] )
        count = K.write_model( target, RMAP.RESOURCE_DIR, name, models[name] )
        print( f"{variant} {name}: {count} triangles, {len( models[name].boxes )} boxes" )
    ( out / "modules.json" ).write_text( json.dumps( loaded, indent=1, sort_keys=True ), encoding="utf-8" )
    if RMAP.MISSING:
        print( "missing:", RMAP.MISSING )


# ---------------------------------------------------------------------------------------------------------------------
# Splicing

def faces( path ):
    """ The OBJ's faces as ( material, corners as text ), with the line index of each face line. """
    v, vt, vn, out = [], [], [], []
    mat = None
    lines = Path( path ).read_text( encoding="utf-8" ).splitlines( keepends=True )
    for index, line in enumerate( lines ):
        if line.startswith( "v " ):
            v.append( line[2:].strip() )
        elif line.startswith( "vt " ):
            vt.append( line[3:].strip() )
        elif line.startswith( "vn " ):
            vn.append( line[3:].strip() )
        elif line.startswith( "usemtl " ):
            mat = line.split( None, 1 )[1].strip()
        elif line.startswith( "f " ):
            corners = []
            for c in line.split()[1:]:
                a = c.split( "/" )
                corners.append( ( v[int( a[0] ) - 1], vt[int( a[1] ) - 1] if len( a ) > 1 and a[1] else "",
                                  vn[int( a[2] ) - 1] if len( a ) > 2 and a[2] else "" ) )
            out.append( ( ( mat, tuple( corners ) ), index ) )
    return lines, out, ( len( v ), len( vt ), len( vn ) )


def bridge_bin( face ):
    """ A face of one of the six footbridge bins: 'Railhead Bridge sign overlap' moves them (already in the code both
    builds loaded) and replaces their faces itself, with this change's corners. The OBJ's v is ( -e, z, n ). """
    for p, _, _ in face[1]:
        a, z, n = ( float( x ) for x in p.split() )
        if not ( abs( a ) <= 1170.0 and 211.0 <= z <= 262.0 and ( -324.0 <= n <= -303.5 or -256.5 <= n <= -236.0 ) ):
            return False
    return True


def _splice_obj( label, path, removed, added ):
    lines, installed, counts = faces( path )
    want = Counter( removed )
    drop = set()
    for face, index in installed:
        if want[face] > 0:
            want[face] -= 1
            drop.add( index )
    missing = sum( want.values() )
    if missing:
        raise SystemExit( f"{label}: {missing} of {sum( removed.values() )} faces to remove aren't in the installed OBJ" )
    kept = [ line for i, line in enumerate( lines ) if i not in drop ]
    if kept and not kept[-1].endswith( "\n" ):
        kept[-1] += "\n"
    nv, nvt, nvn = counts
    by_mat = {}
    for ( mat, corners ), k in added.items():
        by_mat.setdefault( mat, [] ).extend( [ corners ] * k )
    extra_v, extra_f = [], []
    for mat in sorted( by_mat, key=str ):
        extra_f.append( f"usemtl {mat}\n" )
        for corners in by_mat[mat]:
            refs = []
            for p, t, n in corners:
                extra_v.append( f"v {p}\n" )
                nv += 1
                ref = str( nv )
                if t:
                    extra_v.append( f"vt {t}\n" )
                    nvt += 1
                    ref += f"/{nvt}"
                else:
                    ref += "/"
                if n:
                    extra_v.append( f"vn {n}\n" )
                    nvn += 1
                    ref += f"/{nvn}"
                refs.append( ref )
            extra_f.append( "f " + " ".join( refs ) + "\n" )
    return "".join( kept + extra_v + extra_f )


def splice( name, old_dir, new_dir, stage_dir ):
    old = Counter( f for f, _ in faces( old_dir / f"{name}.obj" )[1] )
    new = Counter( f for f, _ in faces( new_dir / f"{name}.obj" )[1] )
    removed, added = old - new, new - old
    skipped = ( 0, 0 )
    if "dress" in name:
        skipped = ( sum( k for f, k in removed.items() if bridge_bin( f ) ), sum( k for f, k in added.items() if bridge_bin( f ) ) )
        removed = Counter( { f: k for f, k in removed.items() if not bridge_bin( f ) } )
        added = Counter( { f: k for f, k in added.items() if not bridge_bin( f ) } )
    files = {}
    stage_dir.mkdir( parents=True, exist_ok=True )
    for copy in COPIES.get( name, ( name, ) ):
        text = _splice_obj( f"{copy}.obj", INSTALLED / f"{copy}.obj", removed, added )
        out = stage_dir / f"{copy}.obj"
        out.parent.mkdir( parents=True, exist_ok=True )
        out.write_text( text, encoding="utf-8", newline="" )
        files[f"models/maps/railhead/{copy}.obj"] = out
    report = { "removed_faces": sum( removed.values() ), "added_faces": sum( added.values() ),
               "bridge_bin_faces_left_out": { "removed": skipped[0], "added": skipped[1] },
               "removed_by_material": dict( Counter( m for ( m, _ ), k in removed.items() for _ in range( k ) ) ),
               "added_by_material": dict( Counter( m for ( m, _ ), k in added.items() for _ in range( k ) ) ) }
    for ext, fn in ( ( "mtl", splice_mtl ), ( "vmdl", splice_vmdl ) ):
        o, n = old_dir / f"{name}.{ext}", new_dir / f"{name}.{ext}"
        if sha( o ) == sha( n ):
            continue
        for copy in ( MTL_COPIES.get( name, ( name, ) ) if ext == "mtl" else ( name, ) ):
            text, changes = fn( copy, o.read_text( encoding="utf-8" ), n.read_text( encoding="utf-8" ),
                                ( INSTALLED / f"{copy}.{ext}" ).read_text( encoding="utf-8" ) )
            report[f"{copy}.{ext}"] = changes
            out = stage_dir / f"{copy}.{ext}"
            out.parent.mkdir( parents=True, exist_ok=True )
            out.write_text( text, encoding="utf-8", newline="" )
            files[f"models/maps/railhead/{copy}.{ext}"] = out
    return report, files


def _remove( name, items, removed ):
    """ items less every item in removed (a Counter), each of which must be there. """
    want = Counter( removed )
    out = []
    for item in items:
        if want[item] > 0:
            want[item] -= 1
        else:
            out.append( item )
    if sum( want.values() ):
        raise SystemExit( f"{name}: {sum( want.values() )} of the lines to remove aren't in the installed file" )
    return out


def splice_mtl( name, old, new, installed ):
    """ An .mtl is one block per material ( newmtl, Kd, d ), sorted by name. """
    def blocks( text ):
        out = []
        for line in text.splitlines( keepends=True ):
            if line.startswith( "newmtl " ) or not out:
                out.append( line )
            else:
                out[-1] += line
        return out
    o, n = Counter( blocks( old ) ), Counter( blocks( new ) )
    removed, added = o - n, n - o
    kept = _remove( f"{name}.mtl", blocks( installed ), removed )
    for block in added.elements():
        kept.append( block )
    kept.sort( key=lambda b: b.split( "\n", 1 )[0] )
    return "".join( kept ), { "removed": sum( removed.values() ), "added": sum( added.values() ) }


def _vmdl_parts( text ):
    """ ( the lines with the remaps and collision boxes taken out, the remap lines, the box blocks ). """
    lines = text.splitlines( keepends=True )
    skeleton, remaps, boxes = [], [], []
    i = 0
    while i < len( lines ):
        line = lines[i]
        if "{ from = " in line and " to = " in line:
            remaps.append( line )
            skeleton.append( "<remap>\n" )
        elif line.strip() == "{" and i + 1 < len( lines ) and lines[i + 1].strip().startswith( '_class = "PhysicsShape' ):
            j = i
            while lines[j].strip() != "},":
                j += 1
            boxes.append( "".join( lines[i:j + 1] ) )
            skeleton.append( "<box>\n" )
            i = j
        else:
            skeleton.append( line )
        i += 1
    collapse = []
    for line in skeleton:
        if line in ( "<remap>\n", "<box>\n" ) and collapse and collapse[-1] == line:
            continue
        collapse.append( line )
    return collapse, remaps, boxes


def splice_vmdl( name, old, new, installed ):
    """ The material remaps and the collision boxes this change takes out and adds; everything else must be the same
    in both builds. The installed file keeps its own order, the added remaps going in by name, the boxes at the end. """
    so, ro, bo = _vmdl_parts( old )
    sn, rn, bn = _vmdl_parts( new )
    if so != sn:
        raise SystemExit( f"{name}.vmdl: the two builds differ outside the remaps and the collision boxes" )
    removed_r, added_r = Counter( ro ) - Counter( rn ), Counter( rn ) - Counter( ro )
    removed_b, added_b = Counter( bo ) - Counter( bn ), Counter( bn ) - Counter( bo )
    lines = installed.splitlines( keepends=True )
    out, i = [], 0
    want_r, want_b = Counter( removed_r ), Counter( removed_b )
    remap_seen = box_seen = False
    while i < len( lines ):
        line = lines[i]
        if "{ from = " in line and " to = " in line:
            remap_seen = True
            if want_r[line] > 0:
                want_r[line] -= 1
            else:
                out.append( line )
            i += 1
            continue
        if line.strip() == "{" and i + 1 < len( lines ) and lines[i + 1].strip().startswith( '_class = "PhysicsShape' ):
            j = i
            while lines[j].strip() != "},":
                j += 1
            block = "".join( lines[i:j + 1] )
            box_seen = True
            if want_b[block] > 0:
                want_b[block] -= 1
            else:
                out.append( block )
            i = j + 1
            nxt = lines[i] if i < len( lines ) else ""
            if not ( nxt.strip() == "{" and i + 1 < len( lines ) and lines[i + 1].strip().startswith( '_class = "PhysicsShape' ) ):
                out.extend( added_b.elements() )
            continue
        out.append( line )
        i += 1
    if sum( want_r.values() ) or sum( want_b.values() ):
        raise SystemExit( f"{name}.vmdl: {sum( want_r.values() )} remaps and {sum( want_b.values() )} boxes to remove "
                          "aren't in the installed file" )
    if ( added_r and not remap_seen ) or ( added_b and not box_seen ):
        raise SystemExit( f"{name}.vmdl: nowhere to put the added remaps or boxes" )
    if added_r:
        # The remaps are one run of lines sorted by name: the added ones go into it in order.
        # The remaps are runs of lines, the generator's own sorted by name (the longest; an import can add its own
        # run): the added ones go into it in order.
        runs = []
        for k, line in enumerate( out ):
            if "{ from = " in line and " to = " in line:
                if runs and runs[-1][-1] == k - 1:
                    runs[-1].append( k )
                else:
                    runs.append( [ k ] )
        run = max( runs, key=len )
        out = out[:run[0]] + sorted( [ out[k] for k in run ] + list( added_r.elements() ) ) + out[run[-1] + 1:]
    return "".join( out ), { "remaps_removed": sum( removed_r.values() ), "remaps_added": sum( added_r.values() ),
                             "boxes_removed": sum( removed_b.values() ), "boxes_added": sum( added_b.values() ) }


def stage():
    old_dir, new_dir = HERE / "paired/old", HERE / "paired/new"
    a = json.loads( ( old_dir / "modules.json" ).read_text( encoding="utf-8" ) )
    b = json.loads( ( new_dir / "modules.json" ).read_text( encoding="utf-8" ) )
    if a != b:
        differ = sorted( k for k in set( a ) | set( b ) if a.get( k ) != b.get( k ) )
        raise SystemExit( f"the two builds loaded different code: {differ}" )
    stage_dir = HERE / "splice-stage/models/maps/railhead"
    reports, publish = {}, {}
    for name in MODELS:
        report, files = splice( name, old_dir / "models/maps/railhead", new_dir / "models/maps/railhead", stage_dir )
        reports[name] = report
        print( name, report["removed_faces"], "removed,", report["added_faces"], "added" )
        for rel, path in files.items():
            publish[rel] = { "source": path.relative_to( ROOT ).as_posix(), "before": sha( ROOT / "Assets" / rel ),
                             "after": sha( path ) }
    material = ROOT / "Assets/materials/railhead/rw_wood_end.vmat"
    staged_material = HERE / "splice-stage/materials/railhead/rw_wood_end.vmat"
    staged_material.parent.mkdir( parents=True, exist_ok=True )
    sys.path.insert( 0, str( TOOLS ) )
    import railhead_prop_materials as PM
    PM.write_bench( staged_material.parent )
    publish["materials/railhead/rw_wood_end.vmat"] = { "source": staged_material.relative_to( ROOT ).as_posix(),
                                                         "before": sha( material ) if material.exists() else None,
                                                         "after": sha( staged_material ) }
    ( HERE / "publish.json" ).write_text( json.dumps( { "files": publish }, indent=1 ), encoding="utf-8" )
    ( HERE / "splice-report.json" ).write_text( json.dumps( { "modules": len( a ), "models": reports }, indent=1 ),
                                                encoding="utf-8" )
    print( f"publish.json: {len( publish )} files" )


if __name__ == "__main__":
    if sys.argv[1] == "build":
        build( sys.argv[2], sys.argv[3] )
    else:
        stage()
