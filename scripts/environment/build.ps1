param([string]$UnityEditor='D:\A-3D\Unity Editors\Editor\Unity.exe',[switch]$SceneOnly)
$ErrorActionPreference='Stop'
$productionRoot=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$projectRoot=Join-Path $productionRoot 'unity'
$outputRoot=Join-Path $projectRoot 'Builds\P0'
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null
$historyRoot=Join-Path $projectRoot 'Logs\build-history'
New-Item -ItemType Directory -Force -Path $historyRoot|Out-Null
$logPath=Join-Path $historyRoot ((Get-Date -Format 'yyyyMMdd-HHmmss-fff')+$(if($SceneOnly){'-scene.log'}else{'-build.log'}))
$previousBuild=$env:ATHENS_PRODUCTION_BUILD
$previousProfile=$env:ALLUSERSPROFILE
try {
    if(-not $env:ALLUSERSPROFILE){$env:ALLUSERSPROFILE=[Environment]::GetFolderPath('CommonApplicationData')}
    $env:ATHENS_PRODUCTION_BUILD=$outputRoot
    $entry=if($SceneOnly){'ProductionBuilder.CreateScene'}else{'ProductionBuilder.BuildWindows'}
    $arguments=@('-batchmode','-quit','-nographics','-projectPath',('"'+$projectRoot+'"'),'-buildTarget','Win64','-executeMethod',$entry,'-logFile',('"'+$logPath+'"'))
    $editorProcess=Start-Process -FilePath $UnityEditor -ArgumentList $arguments -WindowStyle Hidden -PassThru
    $editorProcess.WaitForExit()
    if($editorProcess.ExitCode -ne 0){throw "Production Editor failed ($($editorProcess.ExitCode)); see $logPath"}
    if(-not $SceneOnly -and -not(Test-Path -LiteralPath (Join-Path $outputRoot 'AthensProduction.exe'))){throw "No Player created; see $logPath"}
    [pscustomobject]@{exit_code=$editorProcess.ExitCode;log=$logPath;output=$outputRoot}|ConvertTo-Json
} finally {
    $env:ATHENS_PRODUCTION_BUILD=$previousBuild
    $env:ALLUSERSPROFILE=$previousProfile
}
