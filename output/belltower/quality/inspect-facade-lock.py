"""Read-only Windows Restart Manager query for a chosen Belltower source lock."""
import argparse
import ctypes as c
from ctypes import wintypes as w
import json
from pathlib import Path
import psutil

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--model', choices=('east', 'west'), default='east')
args = parser.parse_args()

class UniqueProcess(c.Structure):
    _fields_ = [('pid', w.DWORD), ('started', w.FILETIME)]

class ProcessInfo(c.Structure):
    _fields_ = [('process', UniqueProcess), ('app', w.WCHAR * 256),
                ('service', w.WCHAR * 64), ('kind', c.c_int),
                ('status', w.ULONG), ('session', w.DWORD), ('restartable', w.BOOL)]

rm = c.WinDLL('rstrtmgr', use_last_error=True)
rm.RmStartSession.argtypes = [c.POINTER(w.DWORD), w.DWORD, w.LPWSTR]
rm.RmRegisterResources.argtypes = [w.DWORD, w.UINT, c.POINTER(w.LPCWSTR), w.UINT, c.c_void_p, w.UINT, c.c_void_p]
rm.RmGetList.argtypes = [w.DWORD, c.POINTER(w.UINT), c.POINTER(w.UINT), c.POINTER(ProcessInfo), c.POINTER(w.DWORD)]
rm.RmEndSession.argtypes = [w.DWORD]
session = w.DWORD()
key = c.create_unicode_buffer(33)
assert rm.RmStartSession(c.byref(session), 0, key) == 0
try:
    path = str(Path(f'Assets/models/maps/belltower/belltower_{args.model}.obj').resolve())
    assert rm.RmRegisterResources(session, 1, (w.LPCWSTR * 1)(path), 0, None, 0, None) == 0
    needed, count, reason = w.UINT(), w.UINT(), w.DWORD()
    result = rm.RmGetList(session, c.byref(needed), c.byref(count), None, c.byref(reason))
    if result == 234:
        infos = (ProcessInfo * needed.value)()
        count.value = needed.value
        result = rm.RmGetList(session, c.byref(needed), c.byref(count), infos, c.byref(reason))
        assert result == 0, result
        records = []
        for info in infos[:count.value]:
            p = psutil.Process(info.process.pid)
            records.append({'pid': p.pid, 'application': info.app, 'name': p.name(), 'command': p.cmdline()})
        print(json.dumps({'file': path, 'locking_processes': records}, indent=2))
    else:
        print(json.dumps({'result': result, 'count': count.value, 'needed': needed.value}))
finally:
    rm.RmEndSession(session)
