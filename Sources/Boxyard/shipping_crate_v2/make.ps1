# Build, bake, paint and export both crates, in Blender at idle priority, then render them against the old ones.
#   make.ps1 <blender runner script> <width> <samples> <render folder> [-NoBuild] [-Views site,close,top,big] [-Which old,new]
param([string]$Run, [string]$Width = '640', [string]$Samples = '28', [string]$Folder = 'pass1', [switch]$NoBuild, [string]$Views = 'site,close,top,big', [string]$Which = 'old,new')
$src = 'C:\sbox-projects\hc1\forked-shooter-main\Sources\Boxyard\shipping_crate_v2'
$root = 'C:\sbox-projects\hc1\forked-shooter-main'
$work = "$root\output\asset-improvement-20261030\shipping-crate"
$assets = "$root\Assets\models\maps\boxyard\shipping_crate_v2"
New-Item -ItemType Directory -Force $work, $assets | Out-Null
foreach ($variant in 'standard', 'large') {
    if (-not $NoBuild) {
        & $Run -Script "$src\crate.py" -Log "$work\$variant-build.log" -Rest @($work, $root, $variant, 'build', 'bake') 2>&1 | Select-String 'tris|islands|parts|Traceback|Error'
    }
    python "$src\paint_crate.py" $work $assets $variant 2>&1 | Select-String -NotMatch 'Warning'
    & $Run -Script "$src\crate.py" -Log "$work\$variant-export.log" -Rest @($work, $root, $variant, 'export') 2>&1 | Select-String 'exported|Traceback|Error'
    python "$root\Sources\Gameplay\capture-flag-v2\check_outward.py" "$assets\crate_${variant}_lod0.obj" "crate_$variant"
}
& $Run -Script "$src\render_crate.py" -Log "$work\$Folder.log" -Rest @($root, "$work\$Folder", $Width, $Samples, $Views, $Which) 2>&1 | Select-String 'renders done|Traceback|Error|polys'
$f = "$work\$Folder"
$cells = @()
foreach ($v in $Views.Split(',')) {
    if ($Which -match 'old') { $cells += "$f\$v-before.png|BEFORE (Blender render)" }
    $cells += "$f\$v-after.png|AFTER (Blender render)"
}
python "$root\Sources\Weapons\he_grenade_v2\sheet.py" "$f\sheet.png" 2 ([int]$Width - 20) @cells
