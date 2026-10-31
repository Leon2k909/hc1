# Build, bake, paint and export the bollard in Blender at idle priority, then render it against the old one.
#   make.ps1 <blender runner script> [-Width 640] [-Samples 28] [-Folder pass1] [-NoBuild] [-Which old,new]
param([string]$Run, [string]$Width = '640', [string]$Samples = '28', [string]$Folder = 'pass1', [switch]$NoBuild, [string]$Views = 'quay,close,harbour,top', [string]$Which = 'old,new')
$src = 'C:\sbox-projects\hc1\forked-shooter-main\Sources\Lowtide\mooring_bollard_v2'
$root = 'C:\sbox-projects\hc1\forked-shooter-main'
$work = "$root\output\asset-improvement-20261030\mooring-bollard"
$assets = "$root\Assets\models\maps\lowtide\mooring_bollard_v2"
New-Item -ItemType Directory -Force $work, $assets | Out-Null
if (-not $NoBuild) {
    & $Run -Script "$src\bollard.py" -Log "$work\build.log" -Rest @($work, $root, 'build', 'bake') 2>&1 | Select-String 'tris|islands|parts|Traceback|Error'
}
python "$src\paint_bollard.py" $work $assets 2>&1 | Select-String -NotMatch 'Warning'
& $Run -Script "$src\bollard.py" -Log "$work\export.log" -Rest @($work, $root, 'export') 2>&1 | Select-String 'exported|Traceback|Error'
python "$root\Sources\Gameplay\capture-flag-v2\check_outward.py" "$assets\mooring_bollard_lod0.obj" mooring_bollard
& $Run -Script "$src\render_bollard.py" -Log "$work\$Folder.log" -Rest @($root, "$work\$Folder", $Width, $Samples, $Views, $Which) 2>&1 | Select-String 'renders done|Traceback|Error|polys'
$f = "$work\$Folder"
$cells = @()
foreach ($v in $Views.Split(',')) {
    if ($Which -match 'old') { $cells += "$f\$v-before.png|BEFORE (Blender render)" }
    $cells += "$f\$v-after.png|AFTER (Blender render)"
}
python "$root\Sources\Weapons\he_grenade_v2\sheet.py" "$f\sheet.png" 2 ([int]$Width - 20) @cells
