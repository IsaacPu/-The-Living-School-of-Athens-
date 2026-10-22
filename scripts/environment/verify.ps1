param([string]$OutputDirectory)
$ErrorActionPreference='Stop'
$productionRoot=Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
if(-not $OutputDirectory){$OutputDirectory=Join-Path $productionRoot ('qa\environment\runs\'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff'))}
$OutputDirectory=[IO.Path]::GetFullPath($OutputDirectory)
$allowedRoot=[IO.Path]::GetFullPath((Join-Path $productionRoot 'qa\environment'))+[IO.Path]::DirectorySeparatorChar
if(-not $OutputDirectory.StartsWith($allowedRoot,[StringComparison]::OrdinalIgnoreCase)){throw 'QA output must stay within production/qa/environment.'}
New-Item -ItemType Directory -Force -Path $OutputDirectory|Out-Null
$playerPath=Join-Path $productionRoot 'unity\Builds\P0\AthensProduction.exe'
$logPath=Join-Path $OutputDirectory 'player.log'
$arguments=@('-force-d3d11','-screen-fullscreen','0','-screen-width','1440','-screen-height','1080','-logFile',('"'+$logPath+'"'),'--verify-production',('"'+$OutputDirectory+'"'))
$playerProcess=Start-Process -FilePath $playerPath -ArgumentList $arguments -WindowStyle Hidden -PassThru
if(-not $playerProcess.WaitForExit(180000)){$playerProcess.Kill();throw "Production QA timed out; see $logPath"}
$reportPath=Join-Path $OutputDirectory 'verification.json'
if(-not(Test-Path -LiteralPath $reportPath)){throw "Player did not write report; exit=$($playerProcess.ExitCode); see $logPath"}
$report=Get-Content -LiteralPath $reportPath -Raw|ConvertFrom-Json
[pscustomobject]@{exit_code=$playerProcess.ExitCode;passed=$report.passed;checks=$report.checks.Count;report=$reportPath}|ConvertTo-Json
if($playerProcess.ExitCode -ne 0 -or -not $report.passed){throw "Production QA failed; inspect $reportPath"}
