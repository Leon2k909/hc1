""" Replaces one top-level function (and any that follow up to a marker) in Tools/riverdale_map.py with a file's text.

    python splice.py <new text file> <first def line> <end marker line>
"""
import sys
from pathlib import Path

ROOT = Path( __file__ ).resolve().parents[5]
path = ROOT / "Tools/riverdale_map.py"
new = Path( sys.argv[1] ).read_text( encoding="utf-8" ).rstrip( "\n" ) + "\n"
start, end = sys.argv[2], sys.argv[3]
s = path.read_text( encoding="utf-8" )
assert s.count( start ) == 1, ( start, s.count( start ) )
i = s.index( start )
j = s.index( end, i )
s = s[:i] + new + "\n\n" + s[j:]
path.write_text( s, encoding="utf-8", newline="\n" )
print( f"spliced {len( new.splitlines() )} lines in place of {s[i:j].count( chr( 10 ) )}" )
