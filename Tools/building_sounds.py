"""
Sounds for Ridgeback's buildings (Tools/ridgeback_buildings.py): the doors' latch, hinge creak and thud, and window
glass shattering. They're synthesised from the physics of what makes them, like Tools/kill_sounds.py, so there are no
samples to license.

    python Tools/building_sounds.py [--preview <wav>]

Writes Assets/sounds/buildings/<name>_<n>.wav, a few takes of each, and each name's .sound event if it doesn't exist
yet (an event may be tuned in the editor, so it isn't overwritten). --preview writes one file that plays every take.

- door_open: the lever turning, the latch bolt drawing back with a click and the lock case's knock, then the hinges
  creaking as the leaf starts to move.
- door_swing: the hinges creaking as a door is pushed shut.
- door_close: the leaf striking the frame, a slab of wood whose lowest bending modes (70-150 Hz for a 46 x 86 inch
  leaf) give the thud, then the latch bolt snapping into its strike plate.
- glass_break: a 3 mm pane (16 inches square) cracking right across, a broadband crack over the pane's own bending
  modes (88 Hz up), then its shards falling onto the sill and the floor. A shard rings at its plate modes: a 3 cm
  piece at ~16 kHz, a 10 cm one at ~1.5 kHz (f = 1.13 pi/2 sqrt(D / rho h) / L^2 for 3 mm float glass). Each lands
  after falling 0.1-1.4 m (0.14-0.53 s) and bounces once or twice, a third as fast each time.

A hinge creak is stick-slip friction: the pin sticks, the leaf's weight builds up, and it slips, over and over at
100-250 times a second, each slip ringing the door and its frame (resonators at 0.4-3 kHz). The rate drifts with the
door's speed.
"""
import argparse
import json
import os
import wave

import numpy as np
from scipy import signal

SR = 44100
ROOT = os.path.join( os.path.dirname( os.path.abspath( __file__ ) ), ".." )
OUT = os.path.join( ROOT, "Assets", "sounds", "buildings" )
SOUND_PATH = "sounds/buildings"

# Name: ( takes, seconds, event settings ). Distance is how far the sound carries (units, as in the guns' events);
# Volume sets it against the guns', whose shots also peak at full scale. The doors' sounds play at the door's origin,
# on its hinge line inside the leaf (TerrorTown.MapMover), where an occlusion trace would always find the leaf, so
# they aren't occluded. A pane breaks where it was, in the open once it's gone.
SOUNDS = {
    "door_open": ( 3, 0.9, dict( Volume="0.45", Pitch="0.96 1.04", Distance=1200, Occlusion=False ) ),
    "door_swing": ( 3, 0.7, dict( Volume="0.3", Pitch="0.95 1.05", Distance=900, Occlusion=False ) ),
    "door_close": ( 3, 0.5, dict( Volume="0.6", Pitch="0.96 1.04", Distance=1600, Occlusion=False ) ),
    "glass_break": ( 4, 1.5, dict( Volume="0.75", Pitch="0.95 1.05", Distance=3000, Occlusion=True ) ),
}

# Float glass's plate constant: pi / 2 * sqrt( D / ( rho h ) ) for h = 3 mm (E 70 GPa, rho 2500 kg/m3, nu 0.22), in
# m^2/s, and the lowest mode's factor for a square piece.
GLASS_PLATE = 7.38
GRAVITY = 9.81


def envelope( t, attack, tau ):
    """ A half-cosine rise over attack seconds, then an exponential decay with time constant tau. """
    rise = 0.5 - 0.5 * np.cos( np.pi * np.clip( t / attack, 0.0, 1.0 ) )
    return rise * np.exp( -np.maximum( t - attack, 0.0 ) / tau )


def modes( t, partials ):
    """ Damped sines, each ( frequency in Hz, amplitude, decay time constant in s ), from t = 0. """
    return sum( a * np.sin( 2 * np.pi * f * t ) * np.exp( -t / tau ) for f, a, tau in partials )


def noise( rng, n, low, high ):
    sos = signal.butter( 2, [ low, min( high, SR / 2 * 0.95 ) ], btype="bandpass", fs=SR, output="sos" )
    y = signal.sosfilt( sos, rng.standard_normal( n ) )
    return y / np.abs( y ).max()


def unit( x ):
    return x / np.abs( x ).max()


def add( out, x, at ):
    """ Mixes x into out starting at `at` seconds, cut at the end. """
    i = int( round( at * SR ) )
    if i >= len( out ):
        return
    n = min( len( x ), len( out ) - i )
    out[i:i + n] += x[:n]


def strike( partials, seconds, attack=0.0002 ):
    """ Modes struck at t = 0: damped sines with a click-free rise. """
    t = np.arange( int( seconds * SR ) ) / SR
    return modes( t, partials ) * envelope( t, attack, 1e9 )


def jitter( rng, partials, spread ):
    return [ ( f * rng.uniform( 1 - spread, 1 + spread ), a, tau ) for f, a, tau in partials ]


# ---------------------------------------------------------------------------------------------------------------------
# Doors

def latch( rng, seconds ):
    """ The lever turning, then the latch bolt drawing back: a small steel click and the lock case's knock. """
    out = np.zeros( int( seconds * SR ) )
    lever = strike( jitter( rng, [ ( 1900, 1.0, 0.010 ), ( 3100, 0.6, 0.007 ), ( 4700, 0.35, 0.005 ) ], 0.08 ), 0.08 )
    add( out, 0.35 * unit( lever ), 0.0 )
    add( out, 0.25 * noise( rng, int( 0.01 * SR ), 2000, 9000 ) * envelope( np.arange( int( 0.01 * SR ) ) / SR, 0.0002, 0.0015 ), 0.0 )
    at = rng.uniform( 0.03, 0.05 )
    bolt = strike( jitter( rng, [ ( 2600, 1.0, 0.012 ), ( 4400, 0.7, 0.008 ), ( 6300, 0.45, 0.006 ), ( 8900, 0.25, 0.004 ) ], 0.06 ), 0.12 )
    case = strike( jitter( rng, [ ( 380, 1.0, 0.020 ), ( 720, 0.6, 0.012 ), ( 1150, 0.3, 0.008 ) ], 0.08 ), 0.12 )
    add( out, 0.8 * unit( bolt ) + 0.45 * unit( case ), at )
    tick = noise( rng, int( 0.006 * SR ), 3000, 12000 ) * envelope( np.arange( int( 0.006 * SR ) ) / SR, 0.0001, 0.001 )
    add( out, 0.5 * tick, at )
    return out


def creak( rng, seconds, loudness=1.0 ):
    """ Stick-slip at the hinge pins: a train of slips whose rate wanders with the leaf's speed, each one ringing the
    leaf and its frame. """
    n = int( seconds * SR )
    t = np.arange( n ) / SR
    base = rng.uniform( 105, 175 )
    # The rate: a slow random glide, faster as the door gets going, with a little flutter.
    drift = signal.sosfiltfilt( signal.butter( 2, 3.0, fs=SR, output="sos" ), rng.standard_normal( n ) )
    drift /= np.abs( drift ).max()
    rate = base * ( 1.0 + 0.35 * drift + 0.25 * np.clip( t / seconds * 1.6, 0, 1 ) ) * ( 1 + 0.02 * np.sin( 2 * np.pi * 7.5 * t ) )
    phase = np.cumsum( rate ) / SR
    pulses = np.zeros( n )
    slips = np.nonzero( np.diff( np.floor( phase ) ) > 0 )[0] + 1
    strength = rng.lognormal( 0.0, 0.25, len( slips ) )
    pulses[slips] = strength
    # Each slip is a quick push rather than an ideal spike.
    pulses = signal.lfilter( np.hanning( 7 ), [ 1.0 ], pulses )

    body = np.zeros( n )
    for f, gain, tau in jitter( rng, [ ( 420, 1.0, 0.012 ), ( 980, 0.8, 0.008 ), ( 1850, 0.55, 0.006 ), ( 3100, 0.3, 0.004 ) ], 0.12 ):
        r = np.exp( -1.0 / ( tau * SR ) )
        body += gain * signal.lfilter( [ 1 - r ], [ 1.0, -2 * r * np.cos( 2 * np.pi * f / SR ), r * r ], pulses )
    friction = noise( rng, n, 900, 3500 ) * 0.12 * signal.lfilter( [ 0.02 ], [ 1.0, -0.98 ], pulses )

    swell = np.clip( t / 0.06, 0, 1 ) * np.clip( ( seconds - t ) / 0.2, 0, 1 ) * ( 0.75 + 0.25 * np.sin( 2 * np.pi * rng.uniform( 1.5, 3 ) * t + rng.uniform( 0, 6 ) ) )
    return loudness * unit( body + friction ) * swell


def door_open( rng, seconds ):
    out = latch( rng, seconds )
    add( out, 0.22 * creak( rng, seconds - 0.12, rng.uniform( 0.7, 1.0 ) ), rng.uniform( 0.07, 0.1 ) )
    return out


def door_swing( rng, seconds ):
    return 0.6 * creak( rng, seconds, rng.uniform( 0.6, 1.0 ) )


def door_close( rng, seconds ):
    """ The leaf strikes the frame: a contact crack, the slab's bending modes, then the latch snapping home and a
    rattle as the leaf settles against its stop. """
    out = np.zeros( int( seconds * SR ) )
    contact = noise( rng, int( 0.03 * SR ), 200, 4000 ) * envelope( np.arange( int( 0.03 * SR ) ) / SR, 0.0003, 0.004 )
    add( out, 0.8 * contact, 0.0 )
    slab = [ ( 78, 1.0, 0.09 ), ( 131, 0.75, 0.07 ), ( 205, 0.55, 0.05 ), ( 310, 0.4, 0.035 ), ( 470, 0.3, 0.025 ),
             ( 720, 0.2, 0.015 ), ( 1100, 0.12, 0.01 ) ]
    add( out, unit( strike( jitter( rng, slab, 0.08 ), seconds, 0.0015 ) ), 0.0 )
    snap = strike( jitter( rng, [ ( 3200, 1.0, 0.010 ), ( 5100, 0.6, 0.007 ), ( 7600, 0.4, 0.005 ) ], 0.06 ), 0.08 )
    at = rng.uniform( 0.01, 0.016 )
    add( out, 0.4 * unit( snap ), at )
    add( out, 0.12 * unit( strike( jitter( rng, [ ( 2900, 1.0, 0.006 ), ( 4800, 0.5, 0.004 ) ], 0.1 ), 0.05 ) ), at + rng.uniform( 0.035, 0.05 ) )
    return out


# ---------------------------------------------------------------------------------------------------------------------
# Glass

def shard( rng, size ):
    """ A shard's ring: its lowest plate mode for its size (m), then higher ones in plate-like ratios. Glass rings
    long in the air, but a shard lying on the floor is damped by what it touches. """
    f = GLASS_PLATE * 2.0 / size ** 2 * rng.uniform( 0.8, 1.25 )
    f = float( np.clip( f, 1200, 17000 ) )
    tau = 0.05 * ( 4000 / f ) ** 0.5
    ratios = [ 1.0, rng.uniform( 1.5, 1.7 ), rng.uniform( 2.1, 2.5 ), rng.uniform( 2.9, 3.4 ) ]
    partials = [ ( f * k, a, tau / k ** 0.6 ) for k, a in zip( ratios, ( 1.0, 0.6, 0.4, 0.22 ) ) if f * k < SR * 0.45 ]
    return strike( partials, min( 0.25, 6 * tau ), 0.00015 )


def glass_break( rng, seconds ):
    """ The break, then the pieces landing, 6 dB down: the crack is the loudest moment, however many pieces land
    together. """
    burst = np.zeros( int( seconds * SR ) )
    out = np.zeros( int( seconds * SR ) )
    t_crack = np.arange( int( 0.05 * SR ) ) / SR
    # The crack running across the pane, and the pane's own low modes as it lets go.
    add( burst, 1.0 * noise( rng, len( t_crack ), 1500, 16000 ) * envelope( t_crack, 0.0002, 0.005 ), 0.0 )
    add( burst, 0.5 * noise( rng, len( t_crack ), 300, 3000 ) * envelope( t_crack, 0.0004, 0.01 ), 0.0 )
    pane = [ ( 88, 1.0, 0.04 ), ( 219, 0.8, 0.03 ), ( 351, 0.6, 0.025 ), ( 440, 0.5, 0.02 ), ( 570, 0.4, 0.015 ) ]
    add( burst, 0.35 * unit( strike( jitter( rng, pane, 0.1 ), 0.3, 0.0008 ) ), 0.0 )

    # Pieces ringing as the pane breaks up, then landing and bouncing.
    count = int( rng.integers( 80, 130 ) )
    sizes = np.exp( rng.uniform( np.log( 0.015 ), np.log( 0.12 ), count ) )
    for size in sizes:
        loud = ( size / 0.12 ) ** 1.1 * rng.lognormal( 0.0, 0.35 )
        if rng.random() < 0.25:
            add( burst, 0.25 * loud * unit( shard( rng, size ) ), rng.uniform( 0.0, 0.03 ) )
        drop = rng.uniform( 0.1, 1.4 )                                  # metres to the sill or the floor
        land = np.sqrt( 2 * drop / GRAVITY ) + rng.uniform( 0.0, 0.05 )
        speed = np.sqrt( 2 * GRAVITY * drop )
        bounces = int( rng.integers( 1, 4 ) )
        for k in range( bounces ):
            ring = unit( shard( rng, size ) )
            add( out, 0.6 * loud * ( 0.3 ** k ) * ring, land )
            if k == 0:
                crunch = int( 0.004 * SR )
                add( out, 0.08 * loud * noise( rng, crunch, 3000, 14000 ) * envelope( np.arange( crunch ) / SR, 0.0001, 0.0008 ), land )
            speed *= 0.3
            land += 2 * speed / GRAVITY
    return unit( burst ) + 0.5 * unit( out )


# ---------------------------------------------------------------------------------------------------------------------
# Writing

def finish( x ):
    """ No rumble under 40 Hz, -1 dBFS peaks, the silent tail cut and faded so it can't click. """
    x = signal.sosfilt( signal.butter( 2, 40, btype="highpass", fs=SR, output="sos" ), x )
    x = unit( np.tanh( 1.2 * unit( x ) ) ) * 10 ** ( -1 / 20 )
    audible = np.nonzero( np.abs( x ) > 10 ** ( -60 / 20 ) )[0]
    end = min( len( x ), audible[-1] + int( 0.01 * SR ) )
    x = x[:end]
    fade = int( 0.015 * SR )
    x[-fade:] *= 0.5 + 0.5 * np.cos( np.linspace( 0, np.pi, fade ) )
    return x


def write_wav( path, x ):
    pcm = np.round( np.clip( x, -1, 1 ) * 32767 ).astype( "<i2" )
    with wave.open( path, "wb" ) as w:
        w.setnchannels( 1 )
        w.setsampwidth( 2 )
        w.setframerate( SR )
        w.writeframes( pcm.tobytes() )


def write_sound_event( name, takes, settings ):
    """ A positional event that falls off with distance, like the guns'. """
    path = os.path.join( OUT, name + ".sound" )
    if os.path.exists( path ):
        return
    event = {
        "UI": False,
        "Volume": settings["Volume"],
        "Pitch": settings["Pitch"],
        "Decibels": 70,
        "SelectionMode": "Random",
        "Sounds": [ f"{SOUND_PATH}/{name}_{k + 1}.vsnd" for k in range( takes ) ],
        "Occlusion": settings["Occlusion"],
        "AirAbsorption": True,
        "Transmission": True,
        "OcclusionRadius": 64,
        "DistanceAttenuation": True,
        "Distance": settings["Distance"],
        "Falloff": [ { "y": 1 }, { "x": 0.25, "y": 0.35, "in": 1.33, "out": -1.33 }, { "x": 1 } ],
        "__references": [],
        "__version": 1,
    }
    with open( path, "w", encoding="utf-8", newline="\n" ) as f:
        json.dump( event, f, indent=2 )
        f.write( "\n" )


def describe( name, x ):
    spectrum = np.abs( np.fft.rfft( x ) )
    freqs = np.fft.rfftfreq( len( x ), 1 / SR )
    head = x[: int( 0.1 * SR )]
    print( f"{name}: {len( x ) / SR:.2f} s, RMS of the first 100 ms {20 * np.log10( np.sqrt( np.mean( head ** 2 ) ) ):.1f} dBFS, "
           f"spectral centroid {np.sum( spectrum * freqs ) / np.sum( spectrum ):.0f} Hz" )


MAKERS = { "door_open": door_open, "door_swing": door_swing, "door_close": door_close, "glass_break": glass_break }


def main():
    parser = argparse.ArgumentParser( description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter )
    parser.add_argument( "--preview", help="also write a WAV that plays every take" )
    args = parser.parse_args()

    os.makedirs( OUT, exist_ok=True )
    parts = []
    for index, ( name, ( takes, seconds, settings ) ) in enumerate( SOUNDS.items() ):
        for k in range( takes ):
            rng = np.random.default_rng( 1000 * ( index + 1 ) + k )
            x = finish( MAKERS[name]( rng, seconds ) )
            write_wav( os.path.join( OUT, f"{name}_{k + 1}.wav" ), x )
            describe( f"{name}_{k + 1}", x )
            parts += [ x * float( settings["Volume"] ), np.zeros( int( 0.6 * SR ) ) ]
        write_sound_event( name, takes, settings )
    if args.preview:
        write_wav( args.preview, np.concatenate( parts ) )
        print( f"preview: {args.preview}" )


if __name__ == "__main__":
    main()
