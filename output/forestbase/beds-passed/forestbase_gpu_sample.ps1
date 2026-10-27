param([int]$Seconds = 45, [string]$OutputPath = 'output/forestbase/bed-runtime-gpu.json')
# Preserve actual overlapping GPU-engine counters, including other active processes.
$samples = [System.Collections.Generic.List[object]]::new()
$sampleDeadline = [DateTime]::UtcNow.AddSeconds($Seconds)
while ([DateTime]::UtcNow -lt $sampleDeadline) {
    $sampleUtc = [DateTime]::UtcNow.ToString('o')
    $counters = Get-CimInstance Win32_PerfFormattedData_GPUPerformanceCounters_GPUEngine |
        Where-Object { $_.Name -match 'engtype_3D' -and $_.UtilizationPercentage -gt 0 }
    foreach ($counter in $counters) {
        $match = [regex]::Match($counter.Name, '^pid_(\d+)_')
        if (-not $match.Success) { continue }
        $sampleProcessId = [int]$match.Groups[1].Value
        $sampleProcess = Get-Process -Id $sampleProcessId -ErrorAction SilentlyContinue
        $samples.Add([pscustomobject]@{
            utc=$sampleUtc; process=$sampleProcess.ProcessName; processId=$sampleProcessId
            engine=$counter.Name; utilizationPercent=$counter.UtilizationPercentage
        })
    }
    Start-Sleep -Milliseconds 900
}
$samples | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $OutputPath -Encoding utf8
Write-Output "Saved $($samples.Count) GPU engine samples to $OutputPath"
