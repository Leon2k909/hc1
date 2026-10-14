$ErrorActionPreference = 'Stop'
$engineRoot = [Environment]::GetEnvironmentVariable('FACEPUNCH_ENGINE', 'User')
if (-not $engineRoot) { $engineRoot = [Environment]::GetEnvironmentVariable('FACEPUNCH_ENGINE', 'Process') }
if (-not $engineRoot) { throw 'FACEPUNCH_ENGINE is not configured.' }
$projectFile = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '../../hc1.sbproj')).Path
$editorPath = Join-Path $engineRoot 'sbox-dev.exe'
# The user requested a visible editor. Launch independently so disconnecting
# an attached CLI cannot close their editor or discard their work.
$editorProcess = Start-Process -FilePath $editorPath -ArgumentList @('-mcp', '-project', ('"' + $projectFile + '"')) -WorkingDirectory $engineRoot -WindowStyle Normal -PassThru
[pscustomobject]@{ Pid = $editorProcess.Id; Project = $projectFile; StartedAt = (Get-Date).ToString('o') } | ConvertTo-Json
