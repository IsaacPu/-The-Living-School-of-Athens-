param([Parameter(Mandatory=$true)][string]$BlenderExe)
$ErrorActionPreference = 'Stop'
$production = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../..'))
$asset = Join-Path $production 'art/characters/plato/v001'
$qa = Join-Path $production 'qa/characters/plato/v001'
New-Item -ItemType Directory -Path $qa -Force | Out-Null
if (-not (Test-Path -LiteralPath $BlenderExe -PathType Leaf)) { throw 'Verified Blender executable is missing.' }
$script = Join-Path $PSScriptRoot 'plato_diagnostic.py'
$invokeRecord = [ordered]@{started_utc=[DateTime]::UtcNow.ToString('o'); executable=$BlenderExe; script=$script; arguments=@('--background','--factory-startup','--python-exit-code','1','--python',$script,'--','--asset-dir',$asset,'--qa-dir',$qa); status='running'}
$invokeRecord | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $qa 'execution.json') -Encoding utf8
& $BlenderExe @($invokeRecord.arguments) 2>&1 | Tee-Object -FilePath (Join-Path $qa 'blender.log') | Where-Object { "$_" -match 'Saved:|CHARACTER_|ERROR|Error|WARNING|Warning|glTF import' }
$exitCode = $LASTEXITCODE
if($exitCode -eq 0){
    $roundtrip = Join-Path $PSScriptRoot 'roundtrip-ruler.py'
    & $BlenderExe --background --factory-startup --python-exit-code 1 --python $roundtrip -- --asset-dir $asset --qa-dir $qa 2>&1 | Tee-Object -FilePath (Join-Path $qa 'roundtrip.log') | Where-Object { "$_" -match 'Saved:|ROUNDTRIP_|ERROR|Error|WARNING|Warning' }
    $exitCode = $LASTEXITCODE
}
if($exitCode -eq 0){
    & python (Join-Path $PSScriptRoot 'package-plato.py')
    $exitCode = $LASTEXITCODE
}
if($exitCode -eq 0){
    & node (Join-Path $PSScriptRoot 'verify-plato.mjs')
    $exitCode = $LASTEXITCODE
}
$invokeRecord['finished_utc']=[DateTime]::UtcNow.ToString('o')
$invokeRecord['exit_code']=$exitCode
$invokeRecord['status']=if($exitCode -eq 0){'completed'}else{'failed'}
$invokeRecord | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $qa 'execution.json') -Encoding utf8
if($exitCode -ne 0){throw "Character diagnostic or packaging failed: $exitCode"}
