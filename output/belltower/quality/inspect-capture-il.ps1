$belltowerEngine = [Environment]::GetEnvironmentVariable('FACEPUNCH_ENGINE', 'User')
if (-not $belltowerEngine) { $belltowerEngine = $env:FACEPUNCH_ENGINE }
if (-not $belltowerEngine) { throw 'FACEPUNCH_ENGINE is unavailable' }
$belltowerManaged = Join-Path $belltowerEngine 'bin/managed'
Add-Type -Path (Join-Path $belltowerManaged 'Mono.Cecil.dll')
$belltowerAssembly = [Mono.Cecil.AssemblyDefinition]::ReadAssembly((Join-Path $belltowerManaged 'Sandbox.Engine.dll'))
try {
    $belltowerCamera = $belltowerAssembly.MainModule.Types | Where-Object FullName -in @('Sandbox.CameraComponent', 'Sandbox.SceneCamera', 'Sandbox.CameraRenderer', 'Sandbox.TonemapSystem')
    $belltowerMethods = $belltowerCamera.Methods | Where-Object Name -in @('RenderToBitmap', 'RenderToTexture', 'InitializeRendering', 'Configure', 'OnPreRender', 'GatherTonemapper', 'UpdateSceneCamera', 'CopyPostProcessing')
    $belltowerMethods += ($belltowerCamera.NestedTypes | Where-Object Name -eq 'AutoExposureSetup').Methods
    $belltowerMethods += ($belltowerAssembly.MainModule.Types | Where-Object FullName -in @('Sandbox.TonemapSystem', 'Sandbox.ToneMapping')).Methods
    $belltowerLines = foreach ($belltowerMethod in $belltowerMethods) {
        $belltowerMethod.FullName
        foreach ($belltowerInstruction in $belltowerMethod.Body.Instructions) {
            $belltowerInstruction.ToString()
        }
    }
    $belltowerReport = Join-Path (Get-Location).Path 'output/belltower/quality/capture-render-il.txt'
    $belltowerLines | Set-Content -LiteralPath $belltowerReport -Encoding UTF8
    'Saved capture IL: ' + $belltowerLines.Count + ' lines'
} finally {
    $belltowerAssembly.Dispose()
}
