param([string]$UnityEditor='D:\A-3D\Unity Editors\Editor\Unity.exe',[switch]$SceneOnly)
$ErrorActionPreference='Stop'
$entranceRoot=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$projectRoot=Join-Path $entranceRoot 'unity'
$outputRoot=Join-Path $projectRoot 'Builds\Entrance'
$historyRoot=Join-Path $entranceRoot 'qa\environment\entrance\build-history'
New-Item -ItemType Directory -Force -Path $outputRoot,$historyRoot | Out-Null
$logPath=Join-Path $historyRoot ((Get-Date -Format 'yyyyMMdd-HHmmss-fff')+'-build.log')
$previousBuild=$env:ATHENS_ENTRANCE_BUILD
$previousProfile=$env:ALLUSERSPROFILE
try {
    if(-not $env:ALLUSERSPROFILE){$env:ALLUSERSPROFILE=[Environment]::GetFolderPath('CommonApplicationData')}
    $env:ATHENS_ENTRANCE_BUILD=$outputRoot
    $entry=if($SceneOnly){'EntranceBuilder.CreateScene'}else{'EntranceBuilder.BuildWindows'}
    $arguments=@('-batchmode','-quit','-nographics','-projectPath',('"'+$projectRoot+'"'),'-buildTarget','Win64','-executeMethod',$entry,'-logFile',('"'+$logPath+'"'))
    $editorProcess=Start-Process -FilePath $UnityEditor -ArgumentList $arguments -WindowStyle Hidden -PassThru
    $editorProcess.WaitForExit()
    if($editorProcess.ExitCode -ne 0){throw "Entrance Editor failed ($($editorProcess.ExitCode)); see $logPath"}
    if(-not $SceneOnly -and -not(Test-Path -LiteralPath (Join-Path $outputRoot 'AthensEntrance.exe'))){throw "No Entrance Player created; see $logPath"}
    [pscustomobject]@{exit_code=$editorProcess.ExitCode;log=$logPath;output=$outputRoot}|ConvertTo-Json
} finally {
    $env:ATHENS_ENTRANCE_BUILD=$previousBuild
    $env:ALLUSERSPROFILE=$previousProfile
}
