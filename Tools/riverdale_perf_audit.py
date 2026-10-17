"""Read-only Riverdale mesh and shadow-cost audit.

    python Tools/riverdale_perf_audit.py

The OBJ triangle counts are the source mesh counts, not the much larger number of
triangles drawn in an engine frame with depth, transparency and shadow passes.
"""

import json
from pathlib import Path


ROOT = Path( __file__ ).resolve().parent.parent
MODELS = ROOT / "Assets/models/maps/riverdale"
SECTORS = ROOT / "Assets/models/maps/riverdale_sectors"
SCENE = ROOT / "Assets/scenes/maps/Riverdale/riverdale.scene"


def mesh_stats( path ):
    data = path.read_bytes()
    return dict( triangles=data.count( b"\nf " ),
                 vertices=data.count( b"\nv " ),
                 material_groups=data.count( b"\nusemtl " ),
                 megabytes=round( len( data ) / 1048576, 2 ) )


def walk( objects ):
    for obj in objects:
        yield obj
        yield from walk( obj.get( "Children", [] ) )


def main():
    meshes = { p.stem: mesh_stats( p ) for folder in ( MODELS, SECTORS )
               for p in folder.glob( "riverdale_*.obj" ) if "_hulls_" not in p.name }
    scene = json.loads( SCENE.read_text( encoding="utf-8" ) )
    renderers = []
    shadowed_lights = []
    for obj in walk( scene["GameObjects"] ):
        for c in obj.get( "Components", [] ):
            if c.get( "__type" ) == "Sandbox.ModelRenderer":
                resource = c.get( "Model" ) or {}
                model_path = resource.get( "Path", "" ) if isinstance( resource, dict ) else resource
                key = Path( model_path ).stem
                row = dict( name=obj["Name"], mesh=key, casts_shadows=c.get( "RenderType" ) == "On" )
                row.update( meshes.get( key, {} ) )
                renderers.append( row )
            if c.get( "__type" ) in ( "Sandbox.SpotLight", "Sandbox.PointLight" ) and c.get( "Shadows" ):
                shadowed_lights.append( obj["Name"] )
    print( "Name                          Tris     Mat groups  Shadows  MiB" )
    for row in sorted( renderers, key=lambda r: r.get( "triangles", 0 ), reverse=True ):
        print( f"{row['name'][:28]:28} {row.get('triangles',0):>9,d} {row.get('material_groups',0):>10,d}"
               f"  {str(row['casts_shadows']):>7}  {row.get('megabytes',0):>6}" )
    print( f"Source triangles in rendered models: {sum(r.get('triangles',0) for r in renderers):,}" )
    print( f"Triangles in shadow-casting models: {sum(r.get('triangles',0) for r in renderers if r['casts_shadows']):,}" )
    print( f"Shadowed direct lights: {len(shadowed_lights)} ({', '.join(shadowed_lights)})" )


if __name__ == "__main__":
    main()
