$ErrorActionPreference = 'Stop'
$enginePath = [Environment]::GetEnvironmentVariable('FACEPUNCH_ENGINE')
if (-not $enginePath) { $enginePath = [Environment]::GetEnvironmentVariable('FACEPUNCH_ENGINE', 'User') }
if (-not $enginePath) { throw 'FACEPUNCH_ENGINE is unavailable' }
$projectFile = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../hc1.sbproj')).Path
$existing = Get-CimInstance Win32_Process -Filter "Name = 'sbox-dev.exe'" | Where-Object { $_.CommandLine -like ('*' + $projectFile + '*') }
if ($existing) { throw 'This project already has an editor; attach to it instead' }
$editor = Start-Process -FilePath (Join-Path $enginePath 'sbox-dev.exe') -ArgumentList ('-project "' + $projectFile + '"') -WorkingDirectory $enginePath -PassThru
[pscustomobject]@{ Pid = $editor.Id; Project = $projectFile } | ConvertTo-Json -Compress
