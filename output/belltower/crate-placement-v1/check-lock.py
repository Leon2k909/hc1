"""Read-only Windows Restart Manager query; does not close or restart processes."""
import ctypes as C
from ctypes import wintypes as W
from pathlib import Path
import json

class Process(C.Structure):
    _fields_ = [('pid', W.DWORD), ('start', W.FILETIME)]

class Info(C.Structure):
    _fields_ = [('process', Process), ('name', W.WCHAR*256), ('service', W.WCHAR*64),
                ('type', W.DWORD), ('status', W.ULONG), ('session', W.DWORD), ('restartable', W.BOOL)]

rm = C.WinDLL('rstrtmgr')
session = W.DWORD(); key = C.create_unicode_buffer(33)
assert rm.RmStartSession(C.byref(session), 0, key) == 0
try:
    filename = str(Path('Assets/models/maps/belltower/belltower_east.obj').resolve())
    paths = (W.LPCWSTR*1)(filename)
    assert rm.RmRegisterResources(session, 1, paths, 0, None, 0, None) == 0
    needed, count, reason = W.UINT(), W.UINT(), W.DWORD()
    rc = rm.RmGetList(session, C.byref(needed), C.byref(count), None, C.byref(reason))
    results = []
    if rc == 234:
        count.value = needed.value; values = (Info*count.value)()
        assert rm.RmGetList(session, C.byref(needed), C.byref(count), values, C.byref(reason)) == 0
        results = [{'pid': x.process.pid, 'name': x.name} for x in values[:count.value]]
    elif rc != 0: raise OSError(rc)
    print(json.dumps({'path': filename, 'holders': results}))
finally:
    rm.RmEndSession(session)
