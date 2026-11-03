from pathlib import Path
import os

path = Path.cwd() / 'CLAUDE.md'
raw = path.read_bytes()
line = b"- [Spillway's canvas cover v2 (`canvas_cover_v2`, B2 loading deck, 2026-11-03)](docs/notes/196-spillway-canvas-cover-v2.md) (2 KB)"
if b'196-spillway-canvas-cover-v2.md' not in raw:
    newline = b'\r\n' if b'\r\n' in raw else b'\n'
    incoming = path.with_name('CLAUDE.md.canvas-incoming')
    incoming.write_bytes(raw + (b'' if raw.endswith(b'\n') else newline) + line + newline)
    assert path.read_bytes() == raw, 'Index changed concurrently; leaving incoming file for review'
    os.replace(incoming, path)
print('Canvas cover note indexed')
