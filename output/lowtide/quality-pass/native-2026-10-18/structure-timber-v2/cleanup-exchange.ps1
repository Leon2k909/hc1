$ErrorActionPreference = 'Stop'
function Get-TaskDigest([string]$targetPath) {
    $algorithm = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($algorithm.ComputeHash([IO.File]::ReadAllBytes($targetPath))).Replace('-', '').ToLowerInvariant() }
    finally { $algorithm.Dispose() }
}
$exchangePath = [IO.Path]::GetFullPath('C:\Users\leon2\AppData\Local\Temp\sbox-cli\9b705a7fa05c489fbc772f40a41b8e93')
$archivePath = Join-Path $PSScriptRoot 'exchange-scripts'
New-Item -ItemType Directory -Path $archivePath -Force | Out-Null
$names = @('state','import','repair','preview','paint','preview-paint','promote','production','rebake','store','reloaded','cleanup-bake','retire-trial','restore-map','final-readback')
$records = @()
foreach ($name in $names) {
    $filePath = [IO.Path]::GetFullPath((Join-Path $exchangePath ('structure-v2-' + $name + '.cs')))
    if ([IO.Path]::GetDirectoryName($filePath) -ne $exchangePath) { throw 'Unexpected exchange path' }
    if (-not (Test-Path -LiteralPath $filePath -PathType Leaf)) { continue }
    $copyPath = Join-Path $archivePath ([IO.Path]::GetFileName($filePath))
    Copy-Item -LiteralPath $filePath -Destination $copyPath -ErrorAction Stop
    $hash = Get-TaskDigest $filePath
    if ($hash -ne (Get-TaskDigest $copyPath)) { throw 'Archive mismatch' }
    Remove-Item -LiteralPath $filePath -ErrorAction Stop
    $records += @{ name = [IO.Path]::GetFileName($filePath); sha256 = $hash.ToLower() }
}
$records | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'exchange-cleanup.json') -Encoding UTF8
Write-Output ('Archived and removed ' + $records.Count + ' task exchange scripts.')
