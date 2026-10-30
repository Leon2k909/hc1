from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
s=(ROOT/'Sources/Collider/console-trial-v1/verify_accepted.py').read_text()
for old,new in (
    ('console integration','cooling-unit integration'),('collider-console-accepted-20261030','collider-cooling-unit-accepted-20261030'),
    ('collider_console as CM','collider_cooling_unit as CM'),('collider_structure','collider_machine'),
    ('==688 and sum(after.values())==27334','==170 and sum(after.values())==45890'),
    ('collider_approved_console','collider_approved_cooling_unit'),('approvedConsoleInstalled','approvedCoolingUnitInstalled'),
    ('oldConsoleTrianglesRemaining','oldCoolingUnitTrianglesRemaining')):
    assert old in s,old;s=s.replace(old,new)
s=s.replace("assert old_doc[old_doc.index(marker):]==doc[doc.index(marker):]",
    "assert (marker in old_doc)==(marker in doc)\nif marker in old_doc:assert old_doc[old_doc.index(marker):]==doc[doc.index(marker):]")
s=s.replace('new=K.Model();CM.append(new);M.configure(new)','new=K.Model();M.cooling_unit(new,-1470);M.configure(new)')
start=s.index('station=K.Model();legacy=K.Model();chair=K.Model();CH.append(chair)')
end=s.index("for path in d['retiredOldStandaloneResources']:",start)
s=s[:start]+'''for east in (-920,-370,180,730,1280):
    a=K.Model();b=K.Model();M.cooling_unit(a,east);M._legacy_cooling_unit(b,east)
    assert tris(a)==tris(b) and plain(a.boxes)==plain(b.boxes),'Other cooling unit changed'
'''+s[end:]
s=s.replace("'stationCollisionUnchanged':True,'otherStationsUnchanged':True", "'authoredCollisionStillAbsent':True,'otherCoolingUnitsUnchanged':True")
s=s.replace('priorAcceptedChairMonitorValvesCaseAndCabinetPreserved','priorAcceptedConsoleChairMonitorValvesCaseAndCabinetPreserved')
(Path(__file__).parent/'verify_accepted.py').write_text(s)
print('Prepared exact cooling-unit scope verification.')
