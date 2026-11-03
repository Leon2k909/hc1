"""Apply the monitor-only generator change without truncating mapped source files."""
from pathlib import Path
root = Path(__file__).resolve().parents[3]
path = root / "Tools/riverdale_hall.py"
data = path.read_bytes()
newline = b"\r\n" if b"\r\n" in data else b"\n"
start = data.index(b"def radiation_monitor( d, fine, face, s, z ):")
end = data.index(b"def eyewash(", start)
replacement = '''def radiation_monitor( d, fine, face, s, z ):
    """ARM-04 enclosure, recessed dose display, pilot lamps and enamel identification plate."""
    import riverdale_radiation_monitor
    riverdale_radiation_monitor.monitor( d, fine, face, s, z )


'''.encode().replace(b"\n", newline)
temporary = path.with_name(path.name + ".arm-writing")
temporary.write_bytes(data[:start] + replacement + data[end:])
temporary.replace(path)
print("Updated radiation_monitor only")
