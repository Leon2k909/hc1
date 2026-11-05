from pathlib import Path
import os

path = Path.cwd() / 'CLAUDE.md'
raw = path.read_bytes()
entry = b"- [Spillway's yard hose v2 (`hose_coil_v2`, 2026-11-03)](docs/notes/197-spillway-yard-hose-v2.md) (2 KB)"
if b'197-spillway-yard-hose-v2.md' not in raw:
    newline = b'\r\n' if b'\r\n' in raw else b'\n'
    incoming = path.with_name('CLAUDE.md.hose-incoming')
    incoming.write_bytes(raw + (b'' if raw.endswith(b'\n') else newline) + entry + newline)
    assert path.read_bytes() == raw, 'Notes changed concurrently; inspect the incoming file.'
    os.replace(incoming, path)
print('Hose note indexed')
