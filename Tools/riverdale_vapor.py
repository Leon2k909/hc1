"""
Cooling-tower water vapor for Riverdale's distant industrial skyline.

The four towers are part of riverdale_backdrop.py. This module adds a separate
draw-only model of soft, crossed vapor sheets above their openings, so there is
no change to routes, collision, lighting, or the backdrop's shadow casting.
It also provides its translucent material to riverdale_materials.py.

The vapor is deliberately sparse: individual wisps overlap into a broken,
wind-sheared plume. The tiny alpha at the silhouettes avoids the hard,
card-shaped edges that otherwise make distant steam look like a game sprite.
"""
import math

import numpy as np
from scipy import ndimage

import map_kit as K
import riverdale_backdrop as BD
import riverdale_materials as RM
import riverdale_parts as P


PAINT = "rv_bd_vapor"


def _noise( rng, n, sigma ):
    """Normalized continuous low-frequency turbulence, with no sharp pixels."""
    field = ndimage.gaussian_filter( rng.standard_normal( ( n, n ) ).astype( np.float32 ),
                                     sigma, mode="reflect" )
    return field / max( float( field.std() ), 1e-5 )


def vapor_material():
    """A translucent, softly sunlit condensation cloud, with transparent edges."""
    n = 512
    rng = np.random.default_rng( 71421 )
    y, x = np.mgrid[0:n, 0:n].astype( np.float32 )
    x = ( x + 0.5 ) * ( 2.0 / n ) - 1.0
    y = 1.0 - ( y + 0.5 ) * ( 2.0 / n )
    broad = _noise( rng, n, 43 )
    lobes = _noise( rng, n, 19 )
    detail = _noise( rng, n, 7 )

    # The centerline kinks slightly, and the jagged lobe outline follows the
    # turbulent density rather than exposing a clean ellipse.
    drift = 0.11 * np.sin( y * 3.6 + 0.6 ) + 0.05 * broad
    r = np.sqrt( ( ( x - drift ) / 0.86 ) ** 2 + ( y / 0.94 ) ** 2 )
    density = 1.0 - r + 0.16 * broad + 0.085 * lobes + 0.028 * detail
    soft = np.clip( ( density + 0.13 ) / 0.55, 0.0, 1.0 )
    soft = soft * soft * ( 3.0 - 2.0 * soft )
    # The plume is seen against the sky: keep it very transparent, with a long
    # feather rather than a recognisable card-shaped or scalloped silhouette.
    alpha = 0.15 * soft * np.clip( 0.78 + 0.10 * lobes + 0.035 * detail, 0.15, 1.0 )
    alpha = ndimage.gaussian_filter( alpha, 3.0, mode="nearest" )
    alpha[:3] = alpha[-3:] = 0
    alpha[:, :3] = alpha[:, -3:] = 0

    sunlight = np.clip( 0.5 + 0.25 * x - 0.1 * y + 0.1 * broad, 0, 1 )
    cold = RM.lin( ( 174, 190, 204 ) )
    warm = RM.lin( ( 222, 219, 209 ) )
    colour = cold[None, None, :] * ( 1 - sunlight[..., None] ) + warm[None, None, :] * sunlight[..., None]
    colour *= ( 0.97 + 0.035 * lobes )[..., None]
    return {
        "colour": np.clip( colour, 0, 1 ).astype( np.float32 ),
        "rough": np.full( ( n, n ), 0.98, np.float32 ),
        "height": np.zeros( ( n, n ), np.float32 ),
        "ppi": n / 512.0,
        "trans": np.clip( alpha, 0, 1 ).astype( np.float32 ),
        "backfaces": True,
        # A surface lit as opaque concrete can turn almost black when viewed
        # against the sky at sunrise. The condensed vapor scatters daylight;
        # a modest self-illumination approximates that ambient scattering.
        "illum": np.ones( ( n, n ), np.float32 ),
        "illum_brightness": 0.85,
        "illum_tint": ( 0.86, 0.89, 0.94 ),
    }


EXTRA_SURFACES = { PAINT: ( 512.0, 0.0, vapor_material ) }


def _sheet( m, center, along, width, height ):
    """A textured vertical plane, two-sided in its material, facing both yards."""
    along = np.asarray( along, dtype=float )
    along /= np.linalg.norm( along )
    c = np.asarray( center, dtype=float )
    left, right = c - np.array( ( along[0], along[1], 0 ) ) * ( width * 0.5 ), c + np.array( ( along[0], along[1], 0 ) ) * ( width * 0.5 )
    half = np.array( ( 0, 0, height * 0.5 ) )
    points = [ left - half, right - half, right + half, left + half ]
    P.card( m, PAINT, points, np.array( ( -along[1], along[0], 0.0 ) ),
            uv=[ ( 0, 0 ), ( 1, 0 ), ( 1, 1 ), ( 0, 1 ) ] )


def extra_models():
    """Non-colliding, non-shadowed condensation above all four tower throats."""
    m = K.Model()
    rng = np.random.default_rng( 2087 )
    for side in ( -1, 1 ):
        for tower_e, tower_n, h in BD.TOWERS:
            e, n = side * tower_e, tower_n
            lip = h + 58.0
            throat = h * 0.235
            # Warm, moist air shears slightly north-west in the prevailing wind.
            wind = np.array( ( -0.86, 0.5 ), float )
            wind /= np.linalg.norm( wind )
            toward_site = np.array( ( -e, -n ), float )
            toward_site /= np.linalg.norm( toward_site )
            face = np.array( ( -toward_site[1], toward_site[0] ) )
            across = np.array( ( -wind[1], wind[0] ) )
            for tier, ( rise, width_factor, height, shear ) in enumerate( (
                ( 225, 1.55, 890, 110 ), ( 735, 1.7, 1100, 390 ),
                ( 1300, 1.82, 1210, 760 ), ( 1930, 1.95, 1310, 1240 ),
            ) ):
                lateral = rng.uniform( -0.12, 0.12 ) * throat
                xy = np.array( ( e, n ) ) + wind * shear + across * lateral
                center = ( float( xy[0] ), float( xy[1] ), lip + rise )
                width = throat * width_factor
                angle = rng.uniform( -0.12, 0.12 )
                a = face * math.cos( angle ) + toward_site * math.sin( angle )
                _sheet( m, center, a, width, height )
                # Two gently overlapping directions are enough to give depth
                # without a dark web of dozens of alpha-sorted intersections.
                _sheet( m, center, toward_site, width * 0.85, height * 0.96 )
    return [ ( "riverdale_vapor", "Cooling Tower Vapor", False, False, m ) ]
