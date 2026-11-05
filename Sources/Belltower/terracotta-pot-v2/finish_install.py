"""Bounded cleanup of read-only diff previews holding the approved targets."""
import subprocess
from pathlib import Path
from native import script,ROOT

command='''$deadline = (Get-Date).AddSeconds(45); $count = 0; while ((Get-Date) -lt $deadline) { $previews = Get-CimInstance Win32_Process -Filter "Name = 'git.exe'" | Where-Object { $_.CommandLine -match '--no-ext-diff' -and $_.CommandLine -match '--numstat' -and $_.CommandLine -match 'Assets/models/maps/belltower/belltower_(east|west).obj' }; foreach ($preview in $previews) { Stop-Process -Id $preview.ProcessId -ErrorAction SilentlyContinue; $count++ }; Start-Sleep -Milliseconds 100 }; Write-Output $count'''
process=subprocess.Popen(['powershell','-NoProfile','-Command',command],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,creationflags=subprocess.CREATE_NO_WINDOW)
try:print(script(ROOT/'Sources/Belltower/terracotta-pot-v2/install.cs.txt','install'),flush=True)
finally:
    if process.poll() is None:process.terminate()
    stdout,stderr=process.communicate(timeout=25)
    print('Read-only diff previews stopped:',stdout,stderr)
