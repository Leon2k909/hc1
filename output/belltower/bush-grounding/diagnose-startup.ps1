$ErrorActionPreference = 'Stop'
$enginePath = [Environment]::GetEnvironmentVariable('FACEPUNCH_ENGINE')
if (-not $enginePath) { $enginePath = [Environment]::GetEnvironmentVariable('FACEPUNCH_ENGINE', 'User') }
$events = Get-WinEvent -FilterHashtable @{LogName='Application'; Id=1000,1001,1026; StartTime=(Get-Date).AddHours(-4)} -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -match '(?i)sbox-dev\.exe|Sandbox\.Engine|Sandbox\.Tools' } |
    Select-Object -First 12 TimeCreated, Id, ProviderName, Message
$events | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'startup-windows-events.json') -Encoding utf8
$dumpRoots = @((Join-Path $env:LOCALAPPDATA 'CrashDumps'), (Join-Path $enginePath 'crash_dumps'), (Join-Path $enginePath 'dumps'))
$dumps = foreach ($folder in $dumpRoots) {
    if (Test-Path -LiteralPath $folder) {
        Get-ChildItem -LiteralPath $folder -File -ErrorAction SilentlyContinue |
            Where-Object { $_.LastWriteTime -gt (Get-Date).AddHours(-4) } |
            Select-Object FullName, Length, LastWriteTime
    }
}
$dumps | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'startup-dumps.json') -Encoding utf8
[pscustomobject]@{Events=@($events); Dumps=@($dumps)} | ConvertTo-Json -Depth 5
