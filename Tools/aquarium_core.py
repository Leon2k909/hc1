"""
Reads the aquarium that my_project generates (tools/aquarium/gen_aquarium.js writes Assets/data/aquarium.txt), for
Tools/oceanarium_map.py, which builds hc1's Oceanarium map round it, and Tools/oceanarium_assets.py, its materials.

The file's format is in its header: parts ( p key name material r g b shadows ), groups ( g ), the part the following
polygons belong to ( m ), flat polygons ( f n nx ny nz (x y z u v)*n ), curved ones with a normal per corner
( s n (x y z nx ny nz u v)*n ), box colliders ( c name cx cy cz hx hy hz yaw ), point lights ( l x y z radius r g b ),
spot lights ( sp x y z pitch yaw radius inner outer r g b shadows ), animal zones ( z ), dirt regions ( k ), and the
hall's ambient light and exposure ( amb, exp ).

Its coordinates are s&box world ( x north, y west, z up ), with the rotunda's centre at the origin, and hc1 places the
hall at the same coordinates: the touch pool's water shader works in world space (g_vRingRect). A polygon's front faces
its normal, and its UVs are as the engine takes them (v down the picture).
"""
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

MY_PROJECT = Path( __file__ ).resolve().parent.parent.parent / "my_project"
DATA_FILE = MY_PROJECT / "Assets" / "data" / "aquarium.txt"


@dataclass
class Part:
    key: str
    name: str
    material: str
    tint: tuple
    shadows: bool


@dataclass
class Poly:
    group: str
    part: str
    points: np.ndarray       # ( n, 3 ) world
    normals: np.ndarray      # ( n, 3 ) one per corner (all the same for a flat polygon)
    uvs: np.ndarray          # ( n, 2 )
    flat: bool


@dataclass
class Collider:
    name: str
    centre: np.ndarray       # world
    half: np.ndarray
    yaw: float               # degrees, about z


@dataclass
class Hall:
    parts: dict = field( default_factory=dict )
    polys: list = field( default_factory=list )
    colliders: list = field( default_factory=list )
    lights: list = field( default_factory=list )     # ( position, radius, colour )
    spots: list = field( default_factory=list )      # ( position, pitch, yaw, radius, inner, outer, colour, shadows )
    ambient: tuple = None
    exposure: tuple = None


def read( path=DATA_FILE, parts_only=False ):
    """ The whole file, or with parts_only just the part table (the file's first lines), which is much quicker. """
    hall = Hall()
    group, part = "Halle", None
    with open( path, encoding="utf-8" ) as f:
        for raw in f:
            t = raw.split()
            if not t or t[0].startswith( "#" ):
                continue
            kind = t[0]
            if parts_only and kind != "p":
                if hall.parts:
                    break
                continue
            if kind == "p":
                hall.parts[t[1]] = Part( t[1], t[2].replace( "_", " " ), t[3], tuple( map( float, t[4:7] ) ), float( t[7] ) > 0.5 )
            elif kind == "g":
                group = " ".join( t[1:] ).replace( "_", " " )
            elif kind == "m":
                part = t[1] if len( t ) > 1 else None
            elif kind == "f":
                n = int( t[1] )
                v = np.array( t[5:], float ).reshape( n, 5 )
                normal = np.array( t[2:5], float )
                hall.polys.append( Poly( group, part, v[:, :3], np.tile( normal, ( n, 1 ) ), v[:, 3:5], True ) )
            elif kind == "s":
                n = int( t[1] )
                v = np.array( t[2:], float ).reshape( n, 8 )
                hall.polys.append( Poly( group, part, v[:, :3], v[:, 3:6], v[:, 6:8], False ) )
            elif kind == "c":
                hall.colliders.append( Collider( t[1].replace( "_", " " ), np.array( t[2:5], float ), np.array( t[5:8], float ),
                                                 float( t[8] ) ) )
            elif kind == "l":
                v = list( map( float, t[1:] ) )
                hall.lights.append( ( np.array( v[0:3] ), v[3], tuple( v[4:7] ) ) )
            elif kind == "sp":
                v = list( map( float, t[1:] ) )
                hall.spots.append( ( np.array( v[0:3] ), v[3], v[4], v[5], v[6], v[7], tuple( v[8:11] ), v[11] > 0.5 ) )
            elif kind == "amb":
                hall.ambient = tuple( map( float, t[1:5] ) )
            elif kind == "exp":
                hall.exposure = tuple( map( float, t[1:4] ) )
    return hall


def collider_corners( c ):
    """ The eight corners of a collider (world). """
    a = np.radians( c.yaw )
    ax = np.array( ( ( np.cos( a ), np.sin( a ), 0.0 ), ( -np.sin( a ), np.cos( a ), 0.0 ), ( 0.0, 0.0, 1.0 ) ) )
    return np.array( [ c.centre + ax[0] * sx * c.half[0] + ax[1] * sy * c.half[1] + ax[2] * sz * c.half[2]
                       for sx in ( -1, 1 ) for sy in ( -1, 1 ) for sz in ( -1, 1 ) ] )
