from pathlib import Path
import os

path = Path.cwd() / 'CLAUDE.md'
raw = path.read_bytes()
entry = b"- [Spillway's turbine wall vent v2 (`wall_vent_v2`, installed 2026-11-04)](docs/notes/198-spillway-wall-vent-v2.md) (2 KB)"
if b'198-spillway-wall-vent-v2.md' not in raw:
    newline = b'\r\n' if b'\r\n' in raw else b'\n'
    incoming = path.with_name('CLAUDE.md.vent-incoming')
    incoming.write_bytes(raw + (b'' if raw.endswith(b'\n') else newline) + entry + newline)
    assert path.read_bytes() == raw, 'Notes changed concurrently; inspect incoming file.'
    os.replace(incoming, path)
print('Vent note indexed')
