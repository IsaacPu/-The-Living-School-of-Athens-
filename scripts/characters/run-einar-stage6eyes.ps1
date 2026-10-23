param([ValidateSet('stage6eyes', 'stage6eyesr1')][string]$RunRecord = 'stage6eyes')
$ErrorActionPreference = 'Stop'
$stage6eyesRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$stage6eyesQa = Join-Path $stage6eyesRoot 'qa/characters/plato/v002/einar-intake'
$stage6eyesStdout = Join-Path $stage6eyesQa ($RunRecord + '.stdout.log')
$stage6eyesStderr = Join-Path $stage6eyesQa ($RunRecord + '.stderr.log')
$stage6eyesRecord = Join-Path $stage6eyesQa ($RunRecord + '-run.json')
$stage6eyesSource = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/project-management/source-cache/einar-v1/extracted/einar_release_v1.blend'
$stage6eyesExe = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/production/.tools/blender/blender-4.5.15-windows-x64/blender.exe'
$stage6eyesExpectedHash = '1c6663da0a2e9d6822978467c244e9186edc76083bae2414e02f9e695e711f7b'
$stage6eyesSourceInfo = Get-Item -LiteralPath $stage6eyesSource
$stage6eyesBeforeHash = (Get-FileHash -LiteralPath $stage6eyesSource -Algorithm SHA256).Hash.ToLowerInvariant()
if ($stage6eyesBeforeHash -ne $stage6eyesExpectedHash -or $stage6eyesSourceInfo.Length -ne 91323760 -or -not $stage6eyesSourceInfo.IsReadOnly) {
    throw 'Approved read-only source preflight mismatch'
}
New-Item -ItemType Directory -Path $stage6eyesQa -Force | Out-Null
if (Test-Path -LiteralPath $stage6eyesRecord) { throw 'Preserve previous invocation record; do not retry implicitly' }
$stage6eyesArgs = @('--background', '--factory-startup', '--disable-autoexec', '--threads', '4', '--python-exit-code', '1', '--python', (Join-Path $PSScriptRoot 'inspect-einar-eyes.py'))
$stage6eyesClock = [Diagnostics.Stopwatch]::StartNew()
$stage6eyesProcess = Start-Process -FilePath $stage6eyesExe -ArgumentList $stage6eyesArgs -WorkingDirectory $stage6eyesRoot -WindowStyle Hidden -RedirectStandardOutput $stage6eyesStdout -RedirectStandardError $stage6eyesStderr -PassThru
$stage6eyesOwnedPid = $stage6eyesProcess.Id
$stage6eyesLimitBytes = [int64](1.2 * 1GB)
$stage6eyesPeakSampled = [int64]0
$stage6eyesPeakReported = [int64]0
$stage6eyesStopReason = $null
$stage6eyesMonitorError = $null
$stage6eyesCleanupError = $null
$stage6eyesExitConfirmed = $false
try {
    while (-not $stage6eyesProcess.HasExited) {
        $stage6eyesProcess.Refresh()
        if ($stage6eyesProcess.HasExited) { break }
        $stage6eyesPeakSampled = [math]::Max($stage6eyesPeakSampled, $stage6eyesProcess.WorkingSet64)
        $stage6eyesPeakReported = [math]::Max($stage6eyesPeakReported, $stage6eyesProcess.PeakWorkingSet64)
        if ($stage6eyesProcess.WorkingSet64 -gt $stage6eyesLimitBytes -or $stage6eyesProcess.PeakWorkingSet64 -gt $stage6eyesLimitBytes) {
            $stage6eyesStopReason = 'working_set_limit_1_2_GiB'
        } elseif ($stage6eyesClock.Elapsed.TotalSeconds -ge 45) {
            $stage6eyesStopReason = 'timeout_45_seconds'
        }
        if ($null -ne $stage6eyesStopReason) { break }
        Start-Sleep -Milliseconds 100
    }
} catch {
    $stage6eyesMonitorError = $_.Exception.Message
    $stage6eyesStopReason = 'monitor_exception'
} finally {
    try {
        # This is the Process handle returned by this exact Start-Process call.
        # Never enumerate/stop another Blender, user P0, Unity or any other app.
        if (-not $stage6eyesProcess.HasExited) {
            if (-not $stage6eyesStopReason) { $stage6eyesStopReason = 'unexpected_monitor_exit' }
            $stage6eyesProcess.Kill()
        }
        $stage6eyesExitConfirmed = $stage6eyesProcess.WaitForExit(5000)
    } catch {
        $stage6eyesCleanupError = $_.Exception.Message
    }
    $stage6eyesClock.Stop()
}
$stage6eyesExitCode = if ($stage6eyesExitConfirmed) { $stage6eyesProcess.ExitCode } else { $null }
$stage6eyesAfterHash = (Get-FileHash -LiteralPath $stage6eyesSource -Algorithm SHA256).Hash.ToLowerInvariant()
$stage6eyesAfterInfo = Get-Item -LiteralPath $stage6eyesSource
$stage6eyesRun = [ordered]@{
    owned_blender_pid = $stage6eyesOwnedPid
    process_exit_code = $stage6eyesExitCode
    process_exit_confirmed = $stage6eyesExitConfirmed
    monitor_error = $stage6eyesMonitorError
    cleanup_error = $stage6eyesCleanupError
    process_wall_seconds = [math]::Round($stage6eyesClock.Elapsed.TotalSeconds, 3)
    maximum_seconds = 45
    working_set_limit_bytes = $stage6eyesLimitBytes
    peak_sampled_working_set_mib = [math]::Round($stage6eyesPeakSampled / 1MB, 2)
    peak_OS_working_set_mib = [math]::Round($stage6eyesPeakReported / 1MB, 2)
    stopped_for_limit = $stage6eyesStopReason
    source_sha256_before = $stage6eyesBeforeHash
    source_sha256_after = $stage6eyesAfterHash
    source_unchanged = ($stage6eyesAfterHash -eq $stage6eyesExpectedHash)
    source_read_only = $stage6eyesAfterInfo.IsReadOnly
    source_bytes = $stage6eyesAfterInfo.Length
    other_processes_stopped = $false
}
$stage6eyesRun | ConvertTo-Json | Set-Content -LiteralPath $stage6eyesRecord -Encoding utf8
$stage6eyesRun | ConvertTo-Json
Get-Content -LiteralPath $stage6eyesStdout -Tail 4
Get-Content -LiteralPath $stage6eyesStderr -Tail 4
if ($stage6eyesStopReason -or $stage6eyesMonitorError -or $stage6eyesCleanupError -or -not $stage6eyesExitConfirmed -or $stage6eyesExitCode -ne 0 -or -not $stage6eyesRun.source_unchanged) { exit 1 }
