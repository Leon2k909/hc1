"""
Rebake the Rotunde's distant cutout into a folder laid out as Assets: export the full model there, then render it in
Blender (Cycles) through the machine-wide GPU queue (output/railhead/stage/.gpu-lock, one render at a time).

    python Tools/railhead_rotunda_rebake.py <root> [--samples 128] [--max-wait 420]

Writes <root>/models/maps/railhead/railhead_rotunda_full.* and <root>/materials/railhead/rotunda_impostor{,_alpha}.png.
For the game, run it with root = Assets (the editor then compiles the two pictures and the full model it ignores).
"""
import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path( __file__ ).resolve().parent
ROOT = HERE.parent
LOCK = ROOT / "output/railhead/stage/.gpu-lock"
BLENDER = r"C:/Program Files/Blender Foundation/Blender 5.1/blender.exe"


def alive( pid ):
    if not pid:
        return False
    kernel = ctypes.windll.kernel32
    handle = kernel.OpenProcess( 0x1000, False, int( pid ) )
    if not handle:
        return False
    code = ctypes.c_ulong()
    kernel.GetExitCodeProcess( handle, ctypes.byref( code ) )
    kernel.CloseHandle( handle )
    return code.value == 259


def stale():
    try:
        owner = json.loads( ( LOCK / "owner.json" ).read_text() )
    except ( OSError, ValueError ):
        try:
            return time.time() - LOCK.stat().st_mtime > 60
        except OSError:
            return False
    return not alive( owner.get( "wrapper" ) ) and not alive( owner.get( "blender" ) )


def main():
    args = sys.argv[1:]
    if not args:
        print( __doc__ )
        sys.exit( 1 )
    root = Path( args[0] ).resolve()
    samples = args[args.index( "--samples" ) + 1] if "--samples" in args else "128"
    max_wait = float( args[args.index( "--max-wait" ) + 1] ) if "--max-wait" in args else 420.0
    sys.path.insert( 0, str( HERE ) )
    import railhead_rotunda_export
    railhead_rotunda_export.export( root )
    start = time.time()
    LOCK.parent.mkdir( parents=True, exist_ok=True )
    while True:
        try:
            LOCK.mkdir()
            break
        except FileExistsError:
            if stale():
                shutil.rmtree( LOCK, ignore_errors=True )
                continue
            if time.time() - start > max_wait:
                print( f"the GPU is still busy after {max_wait:.0f} s; try again later" )
                sys.exit( 3 )
            time.sleep( 3 )
    try:
        child = subprocess.Popen( [ BLENDER, "-b", "--factory-startup", "--python", str( HERE / "railhead_rotunda_bake.py" ),
                                    "--", "--stage", str( root ), "--samples", samples ], cwd=ROOT )
        ( LOCK / "owner.json" ).write_text( json.dumps( { "wrapper": os.getpid(), "blender": child.pid, "args": args } ) )
        code = child.wait()
    finally:
        shutil.rmtree( LOCK, ignore_errors=True )
    print( f"baked in {time.time() - start:.0f} s" )
    sys.exit( code )


if __name__ == "__main__":
    main()
