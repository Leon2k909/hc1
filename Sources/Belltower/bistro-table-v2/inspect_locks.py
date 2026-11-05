import json,subprocess
command=r'''Get-CimInstance Win32_Process -Filter "Name = 'git.exe'" | Where-Object { $_.CommandLine -match 'belltower_(east|west).obj' } | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress'''
p=subprocess.run(['powershell','-NoProfile','-Command',command],capture_output=True,text=True)
rows=json.loads(p.stdout or '[]');rows=rows if isinstance(rows,list) else [rows]
print(json.dumps({'count':len(rows),'first':rows[:4],'errors':p.stderr}))
