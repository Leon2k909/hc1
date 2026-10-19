"""
Side-by-side sheets of Cerro Blanco's captures before and after a pass: python Tools/cerroblanco_compare.py <before> <after>
[--out <png>]. Each view in both folders (output/cerroblanco/captures-v2/<folder>/<name>.png) becomes a row, before on the
left, with its name.
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path( __file__ ).resolve().parent.parent


def main():
    parser = argparse.ArgumentParser( description=__doc__ )
    parser.add_argument( "before", type=Path )
    parser.add_argument( "after", type=Path )
    parser.add_argument( "--out", type=Path )
    parser.add_argument( "--width", type=int, default=800 )
    args = parser.parse_args()
    names = sorted( p.stem for p in args.after.glob( "*.png" ) if ( args.before / p.name ).exists() )
    w = args.width
    h = int( w * 9 / 16 )
    sheet = Image.new( "RGB", ( w * 2 + 12, ( h + 28 ) * len( names ) ), ( 24, 24, 26 ) )
    draw = ImageDraw.Draw( sheet )
    face = ImageFont.truetype( str( ROOT / "Assets/fonts/Dinish-Bold.ttf" ), 18 )
    for row, name in enumerate( names ):
        y = row * ( h + 28 )
        draw.text( ( 8, y + 4 ), f"{name}: before / after", font=face, fill=( 230, 230, 226 ) )
        for col, folder in enumerate( ( args.before, args.after ) ):
            with Image.open( folder / f"{name}.png" ) as im:
                sheet.paste( im.convert( "RGB" ).resize( ( w, h ), Image.LANCZOS ), ( col * ( w + 12 ), y + 26 ) )
    out = args.out or ( args.after.parent / f"compare-{args.after.name}.png" )
    sheet.save( out )
    print( f"wrote {out} ({len( names )} views)" )


if __name__ == "__main__":
    main()
