# Paint the scan-based finish at idle priority into first_aid_v2/scanned/ and write its material, first_aid_scanned.vmat, which the model uses by default. The code-painted first_aid.vmat stays beside it.
$root = 'C:\sbox-projects\hc1\forked-shooter-main'
$src = "$root\Sources\Riverdale\first-aid-v2"
$work = "$root\output\asset-improvement-20261030\first-aid"
$scanned = "$root\Assets\models\maps\riverdale\first_aid_v2\scanned"
New-Item -ItemType Directory -Force $scanned | Out-Null
$p = Start-Process -FilePath 'python' -ArgumentList @('-B', "$src\paint_first_aid.py", $work, $scanned, 'scans') -PassThru -NoNewWindow -RedirectStandardOutput "$work\paint_scanned.log" -RedirectStandardError "$work\paint_scanned.err"
$p.PriorityClass = 'Idle'
$p.WaitForExit()
Get-Content "$work\paint_scanned.log"
Get-Content "$work\paint_scanned.err" | Select-String -Pattern 'Traceback|Error|error:' -Context 0,10 | ForEach-Object { '! ' + $_.ToString() }
$folder = 'models/maps/riverdale/first_aid_v2/scanned'
(Get-Content -Raw "$root\Assets\models\maps\riverdale\first_aid_v2\first_aid.vmat").Replace('models/maps/riverdale/first_aid_v2/first_aid_', "$folder/first_aid_") | Set-Content -NoNewline -Encoding utf8NoBOM "$scanned\first_aid_scanned.vmat"
Get-ChildItem $scanned | ForEach-Object { $_.Name }
