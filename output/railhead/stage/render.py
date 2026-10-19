"""Staged Railhead renders for agents working in parallel: one Cycles render on the GPU at a time, so the shared s&box
editor keeps its video memory.

    python output/railhead/stage/render.py --stage <abs dir> --out <abs dir> [--views a,b] [--view name,e,n,z,te,tn,tz,fov]
        [--size 960x540] [--samples 32] [... any other Tools/railhead_render.py option]

It waits for the lock (output/railhead/stage/.gpu-lock) at most --max-wait seconds (default 420), then exits 3 without
rendering, so a Bash call never runs into its 10-minute limit while queueing. A lock whose render has died is taken
over.
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
ROOT = HERE.parents[2]
LOCK = HERE / ".gpu-lock"
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
        # Just made, or its owner died before writing: give it a minute.
        try:
            return time.time() - LOCK.stat().st_mtime > 60
        except OSError:
            return False
    return not alive( owner.get( "wrapper" ) ) and not alive( owner.get( "blender" ) )


def main():
    args = sys.argv[1:]
    max_wait = 420.0
    if "--max-wait" in args:
        at = args.index( "--max-wait" )
        max_wait = float( args[at + 1] )
        del args[at:at + 2]
    start = time.time()
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
    waited = time.time() - start
    try:
        child = subprocess.Popen( [ BLENDER, "-b", "--factory-startup", "--python", str( ROOT / "Tools/railhead_render.py" ),
                                    "--", *args ], cwd=ROOT )
        ( LOCK / "owner.json" ).write_text( json.dumps( { "wrapper": os.getpid(), "blender": child.pid, "args": args } ) )
        code = child.wait()
    finally:
        shutil.rmtree( LOCK, ignore_errors=True )
    print( f"waited {waited:.0f} s for the GPU, rendered in {time.time() - start - waited:.0f} s" )
    sys.exit( code )


if __name__ == "__main__":
    main()
