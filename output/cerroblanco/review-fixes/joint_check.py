""" Checks the panel shader's box-filtered joint against a brute-force box filter of the true joint, along one axis,
and what the bevel's point-sampled tilt does compared with its true footprint average. """
import numpy as np
S, J, W = 30.0, 0.5, 0.16
def truth_joint( s ):          # s: inches along the axis; joint where within J/2 of a multiple of S
    d = np.abs( ( s + S / 2 ) % S - S / 2 )
    return ( d < J / 2 ).astype( float )
def shader_cover( s, fp ):
    local = ( s / S ) % 1.0
    e = np.minimum( local, 1 - local ) * S
    fp = max( fp, .004 )
    return np.clip( ( np.minimum( e + fp / 2, J / 2 ) - np.maximum( e - fp / 2, -J / 2 ) ) / fp, 0, 1 )
def old_joint( s, aa ):
    local = ( s / S ) % 1.0
    e = np.minimum( local, 1 - local ) * S
    t = np.clip( ( e - ( J / 2 - aa ) ) / ( 2 * aa ), 0, 1 )
    return 1 - t * t * ( 3 - 2 * t )
def bevel_slope( s ):          # signed tilt the shader adds (x component), before attenuation
    local = ( s / S ) % 1.0
    e = np.minimum( local, 1 - local ) * S
    b = np.clip( ( e - J / 2 ) / W, 0, 1 )
    slope = 6 * b * ( 1 - b ) * .08 / W
    return np.where( local < .5, 1, -1 ) * slope
rng = np.random.default_rng( 1 )
print( "fp(in)  max|shader-truth|  mean shader  mean truth  old mean  old at joint centre" )
for fp in ( .05, .2, .5, 1, 2, 5, 10, 20, 29, 40 ):
    xs = rng.uniform( 0, S, 4000 )
    sub = np.linspace( -.5, .5, 801 )
    tr = np.array( [ truth_joint( x + sub * fp ).mean() for x in xs ] )
    sh = shader_cover( xs, fp )
    aa = fp * 2 ** .5 * .35          # aa for an isotropic footprint fp
    aa = max( aa, .008 )
    print( f"{fp:6.2f}  {np.abs( sh - tr ).max():.4f}            {sh.mean():.4f}      {tr.mean():.4f}     {old_joint( xs, aa ).mean():.4f}    {old_joint( np.array( [ 0.0 ] ), aa )[0]:.3f}" )
print()
print( "bevel: fp(in)  shader rms tilt (point, attenuated)  true footprint-mean rms tilt" )
for fp in ( .1, .2, .4, .8, 1.6, 3, 6 ):
    xs = rng.uniform( 0, S, 20000 )
    aa = max( fp * 2 ** .5 * .35, .008 )
    att = min( 1, W / max( aa * 2, .001 ) )
    sh = bevel_slope( xs ) * att
    sub = np.linspace( -.5, .5, 401 )
    tr = np.array( [ bevel_slope( x + sub * fp ).mean() for x in xs[:4000] ] )
    near = np.abs( xs[:4000] % S ) < 3       # pixels within 3 inches of a joint
    print( f"   {fp:5.2f}      {np.sqrt( ( sh ** 2 ).mean() ):.4f} (max {np.abs( sh ).max():.3f})        {np.sqrt( ( tr ** 2 ).mean() ):.4f} (max {np.abs( tr ).max():.3f})" )
