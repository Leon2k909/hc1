# Copy the export into Assets. An open editor compiles it from there by itself.
$root = 'C:\sbox-projects\hc1\forked-shooter-main'
$to = "$root\Assets\Weapons\Throwable\Flashbang\flashbang_v2"
New-Item -ItemType Directory -Force $to | Out-Null
Copy-Item "$root\output\asset-improvement-20261030\flashbang\export\*" $to -Force
"installed $((Get-ChildItem $to).Count) files"
