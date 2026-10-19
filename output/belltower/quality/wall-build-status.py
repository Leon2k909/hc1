from pathlib import Path
import ctypes as C
from ctypes import wintypes as T
from datetime import datetime

root=Path(__file__).resolve().parents[3]
for name in ('belltower_west','belltower_east'):
    for ext in ('.obj','.vmdl_c'):
        path=root/'Assets/models/maps/belltower'/f'{name}{ext}'
        print(path.name,datetime.fromtimestamp(path.stat().st_mtime).isoformat(),round(path.stat().st_size/1048576,1),'MB')
class Entry(C.Structure):
    _fields_=[('dwSize',T.DWORD),('cntUsage',T.DWORD),('th32ProcessID',T.DWORD),('th32DefaultHeapID',C.c_size_t),('th32ModuleID',T.DWORD),('cntThreads',T.DWORD),('th32ParentProcessID',T.DWORD),('pcPriClassBase',T.LONG),('dwFlags',T.DWORD),('szExeFile',T.WCHAR*260)]
k=C.WinDLL('kernel32',use_last_error=True)
k.CreateToolhelp32Snapshot.restype=T.HANDLE
k.OpenProcess.restype=T.HANDLE
k.OpenProcess.argtypes=[T.DWORD,T.BOOL,T.DWORD]
k.GetProcessTimes.argtypes=[T.HANDLE,C.POINTER(T.FILETIME),C.POINTER(T.FILETIME),C.POINTER(T.FILETIME),C.POINTER(T.FILETIME)]
k.CloseHandle.argtypes=[T.HANDLE]
handle=k.CreateToolhelp32Snapshot(2,0)
entry=Entry();entry.dwSize=C.sizeof(entry)
ok=k.Process32FirstW(handle,C.byref(entry))
while ok:
    if any(v in entry.szExeFile.lower() for v in ('sbox','resourcecompiler','python','rtk')):
        process=k.OpenProcess(0x1000,False,entry.th32ProcessID)
        times=[T.FILETIME() for _ in range(4)]
        k.GetProcessTimes(process,*[C.byref(v) for v in times])
        cpu=sum((v.dwHighDateTime<<32)|v.dwLowDateTime for v in times[2:])/1e7
        k.CloseHandle(process)
        print(entry.th32ProcessID,entry.szExeFile,'parent',entry.th32ParentProcessID,'CPU seconds',round(cpu,1),'threads',entry.cntThreads)
    ok=k.Process32NextW(handle,C.byref(entry))
k.CloseHandle(handle)
logs=Path('D:/SteamLibrary/steamapps/common/sbox/logs')
latest=sorted(logs.glob('*.log'),key=lambda p:p.stat().st_mtime,reverse=True)[:1]
for path in latest:
    print('Latest engine log',path.name)
    print('\n'.join(path.read_text(encoding='utf-8',errors='replace').splitlines()[-12:]))
