param([string]$OutputDirectory,[switch]$PreviewOnly)
$ErrorActionPreference='Stop'
$entranceRoot=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if(-not $OutputDirectory){$OutputDirectory=Join-Path $entranceRoot ('qa\environment\entrance\runs\'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff'))}
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
$allowedRoot=[IO.Path]::GetFullPath((Join-Path $entranceRoot 'qa\environment\entrance\runs'))+[IO.Path]::DirectorySeparatorChar
if(-not $OutputDirectory.StartsWith($allowedRoot,[StringComparison]::OrdinalIgnoreCase)){throw 'Entrance QA output must stay within this worktree qa/environment/entrance/runs.'}
New-Item -ItemType Directory -Force -Path $OutputDirectory|Out-Null
if(Test-Path -LiteralPath (Join-Path $OutputDirectory 'report.json')){throw 'Use a new output directory to preserve previous reports.'}
$playerPath=Join-Path $entranceRoot 'unity\Builds\Entrance\AthensEntrance.exe'
$logPath=Join-Path $OutputDirectory 'player.log'
$verificationFlag=if($PreviewOnly){'--preview-entrance'}else{'--verify-entrance'}
$arguments=@('-force-d3d11','-screen-fullscreen','0','-screen-width','1200','-screen-height','900','-logFile',('"'+$logPath+'"'),$verificationFlag,('"'+$OutputDirectory+'"'))
$playerProcess=Start-Process -FilePath $playerPath -ArgumentList $arguments -WindowStyle Hidden -PassThru
if(-not $playerProcess.WaitForExit(330000)){$playerProcess.Kill();throw "Entrance QA timed out; see $logPath"}
$reportPath=Join-Path $OutputDirectory 'report.json'
if(-not(Test-Path -LiteralPath $reportPath)){throw "Player did not write report; exit=$($playerProcess.ExitCode); see $logPath"}
$report=Get-Content -LiteralPath $reportPath -Raw|ConvertFrom-Json
[pscustomobject]@{exit_code=$playerProcess.ExitCode;passed=$report.passed;checks=$report.checks.Count;report=$reportPath}|ConvertTo-Json
if($playerProcess.ExitCode -ne 0 -or -not $report.passed){throw "Entrance QA failed; inspect $reportPath"}
