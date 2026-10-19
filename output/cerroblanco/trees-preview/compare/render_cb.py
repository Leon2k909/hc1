"""Scratch wrapper: Tools/railhead_render.py on Cerro Blanco's scene, with an overlay root searched before Assets.

    blender -b --factory-startup --python render_cb.py -- <overlay root or -> [railhead_render args...]
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path( r"D:/Documents/s&box projects/hc1/forked-shooter-main" )
sys.path.insert( 0, str( ROOT / "Tools" ) )
sys.path.insert( 0, str( Path( __file__ ).parent / "shim" ) )
argv = sys.argv[sys.argv.index( "--" ) + 1:]
overlay = argv.pop( 0 )
sys.argv = sys.argv[:sys.argv.index( "--" ) + 1] + argv

import railhead_render as RR


class Overlay:
    def __init__( self, *roots ):
        self.roots = roots

    def __truediv__( self, rel ):
        for r in self.roots:
            p = r / rel
            if p.exists():
                return p
        return self.roots[-1] / rel


RR.SCENE = ROOT / "Assets/scenes/maps/CerroBlanco/cerroblanco.scene"
roots = ( ( Path( overlay ), ) if overlay != "-" else () ) + ( ROOT / "Assets", )
RR.ASSETS = Overlay( *roots )
RR.TEMP = Path( tempfile.gettempdir() ) / "hc1_cerroblanco_render"
RR.CACHE = RR.TEMP / "cache"
_read = RR.read_scene


def read_scene():
    found = _read()
    found["models"] = [ ( m.get( "Path" ) if isinstance( m, dict ) else m, w, t ) for m, w, t in found["models"] ]
    found["models"] = [ x for x in found["models"] if x[0] ]
    return found


RR.read_scene = read_scene
_map_model = RR.map_model


def map_model( path ):
    # The woods cast no shadows in the game (their renderer's RenderType is Off).
    objects = _map_model( path )
    if "woods" in path:
        for o in objects:
            for slot in o.material_slots:
                no_shadow( slot.material )
    return objects


DONE = set()


def no_shadow( mat ):
    """ Transparent to shadow rays (setting the object's visible_shadow off left the cards ghostly in Cycles). """
    if mat is None or mat.name in DONE:
        return
    DONE.add( mat.name )
    nt = mat.node_tree
    out = next( n for n in nt.nodes if n.type == "OUTPUT_MATERIAL" )
    src = out.inputs["Surface"].links[0].from_socket
    path = nt.nodes.new( "ShaderNodeLightPath" )
    clear = nt.nodes.new( "ShaderNodeBsdfTransparent" )
    mix = nt.nodes.new( "ShaderNodeMixShader" )
    nt.links.new( path.outputs["Is Shadow Ray"], mix.inputs[0] )
    nt.links.new( src, mix.inputs[1] )
    nt.links.new( clear.outputs[0], mix.inputs[2] )
    nt.links.new( mix.outputs[0], out.inputs["Surface"] )


RR.map_model = map_model
_set_camera = RR.set_camera


def set_camera( *args ):
    # Rays through many woods' cards in a row went black at railhead_render's 16 transparent bounces.
    RR.bpy.context.scene.cycles.transparent_max_bounces = 128
    return _set_camera( *args )


RR.set_camera = set_camera
RR.main()
