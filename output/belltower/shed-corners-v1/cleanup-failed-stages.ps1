$shedBase = [System.IO.Path]::GetFullPath('C:\sbox-projects\hc1\forked-shooter-main\output\belltower\shed-corners-v1').TrimEnd('\')
$shedTargets = @((Join-Path $shedBase 'r1'), (Join-Path $shedBase 'r3'))
foreach ($shedTarget in $shedTargets) {
    if (-not (Test-Path -LiteralPath $shedTarget)) { continue }
    $shedResolved = (Resolve-Path -LiteralPath $shedTarget).ProviderPath
    if (-not $shedResolved.StartsWith($shedBase + '\', [System.StringComparison]::OrdinalIgnoreCase) -or
        -not [System.String]::Equals($shedResolved, $shedTarget, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'Failed-stage path resolved outside this task.'
    }
    if ((Get-Item -LiteralPath $shedResolved).Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        throw 'Do not follow a junction during task cleanup.'
    }
}
foreach ($shedTarget in $shedTargets) {
    if (Test-Path -LiteralPath $shedTarget) {
        Remove-Item -LiteralPath $shedTarget -Recurse -Force
        Write-Output ('Removed unused task staging: ' + $shedTarget)
    }
}
