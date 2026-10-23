param([ValidateSet('stage6headref', 'stage6headrefr1')][string]$RunRecord = 'stage6headref')
$ErrorActionPreference = 'Stop'
$stage6headrefRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$stage6headrefQa = Join-Path $stage6headrefRoot 'qa/characters/plato/v002/einar-intake'
$stage6headrefStdout = Join-Path $stage6headrefQa ($RunRecord + '.stdout.log')
$stage6headrefStderr = Join-Path $stage6headrefQa ($RunRecord + '.stderr.log')
$stage6headrefRecord = Join-Path $stage6headrefQa ($RunRecord + '-run.json')
$stage6headrefSource = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/project-management/source-cache/einar-v1/extracted/einar_release_v1.blend'
$stage6headrefExe = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/production/.tools/blender/blender-4.5.15-windows-x64/blender.exe'
$stage6headrefExpectedHash = '1c6663da0a2e9d6822978467c244e9186edc76083bae2414e02f9e695e711f7b'
$stage6headrefSourceInfo = Get-Item -LiteralPath $stage6headrefSource
$stage6headrefBeforeHash = (Get-FileHash -LiteralPath $stage6headrefSource -Algorithm SHA256).Hash.ToLowerInvariant()
if ($stage6headrefBeforeHash -ne $stage6headrefExpectedHash -or $stage6headrefSourceInfo.Length -ne 91323760 -or -not $stage6headrefSourceInfo.IsReadOnly) {
    throw 'Approved read-only source preflight mismatch'
}
New-Item -ItemType Directory -Path $stage6headrefQa -Force | Out-Null
if (Test-Path -LiteralPath $stage6headrefRecord) { throw 'Preserve previous invocation record; do not retry implicitly' }
$stage6headrefArgs = @('--background', '--factory-startup', '--disable-autoexec', '--threads', '4', '--python-exit-code', '1', '--python', (Join-Path $PSScriptRoot 'inspect-einar-head-transform.py'))
$stage6headrefClock = [Diagnostics.Stopwatch]::StartNew()
$stage6headrefProcess = Start-Process -FilePath $stage6headrefExe -ArgumentList $stage6headrefArgs -WorkingDirectory $stage6headrefRoot -WindowStyle Hidden -RedirectStandardOutput $stage6headrefStdout -RedirectStandardError $stage6headrefStderr -PassThru
$stage6headrefOwnedPid = $stage6headrefProcess.Id
$stage6headrefLimitBytes = [int64](1.2 * 1GB)
$stage6headrefPeakSampled = [int64]0
$stage6headrefPeakReported = [int64]0
$stage6headrefStopReason = $null
$stage6headrefMonitorError = $null
$stage6headrefCleanupError = $null
$stage6headrefExitConfirmed = $false
try {
    while (-not $stage6headrefProcess.HasExited) {
        $stage6headrefProcess.Refresh()
        if ($stage6headrefProcess.HasExited) { break }
        $stage6headrefPeakSampled = [math]::Max($stage6headrefPeakSampled, $stage6headrefProcess.WorkingSet64)
        $stage6headrefPeakReported = [math]::Max($stage6headrefPeakReported, $stage6headrefProcess.PeakWorkingSet64)
        if ($stage6headrefProcess.WorkingSet64 -gt $stage6headrefLimitBytes -or $stage6headrefProcess.PeakWorkingSet64 -gt $stage6headrefLimitBytes) {
            $stage6headrefStopReason = 'working_set_limit_1_2_GiB'
        } elseif ($stage6headrefClock.Elapsed.TotalSeconds -ge 45) {
            $stage6headrefStopReason = 'timeout_45_seconds'
        }
        if ($null -ne $stage6headrefStopReason) { break }
        Start-Sleep -Milliseconds 100
    }
} catch {
    $stage6headrefMonitorError = $_.Exception.Message
    $stage6headrefStopReason = 'monitor_exception'
} finally {
    try {
        # This is the Process handle returned by this exact Start-Process call.
        # Never enumerate/stop another Blender, user P0, Unity or any other app.
        if (-not $stage6headrefProcess.HasExited) {
            if (-not $stage6headrefStopReason) { $stage6headrefStopReason = 'unexpected_monitor_exit' }
            $stage6headrefProcess.Kill()
        }
        $stage6headrefExitConfirmed = $stage6headrefProcess.WaitForExit(5000)
    } catch {
        $stage6headrefCleanupError = $_.Exception.Message
    }
    $stage6headrefClock.Stop()
}
$stage6headrefExitCode = if ($stage6headrefExitConfirmed) { $stage6headrefProcess.ExitCode } else { $null }
$stage6headrefAfterHash = (Get-FileHash -LiteralPath $stage6headrefSource -Algorithm SHA256).Hash.ToLowerInvariant()
$stage6headrefAfterInfo = Get-Item -LiteralPath $stage6headrefSource
$stage6headrefRun = [ordered]@{
    owned_blender_pid = $stage6headrefOwnedPid
    process_exit_code = $stage6headrefExitCode
    process_exit_confirmed = $stage6headrefExitConfirmed
    monitor_error = $stage6headrefMonitorError
    cleanup_error = $stage6headrefCleanupError
    process_wall_seconds = [math]::Round($stage6headrefClock.Elapsed.TotalSeconds, 3)
    maximum_seconds = 45
    working_set_limit_bytes = $stage6headrefLimitBytes
    peak_sampled_working_set_mib = [math]::Round($stage6headrefPeakSampled / 1MB, 2)
    peak_OS_working_set_mib = [math]::Round($stage6headrefPeakReported / 1MB, 2)
    stopped_for_limit = $stage6headrefStopReason
    source_sha256_before = $stage6headrefBeforeHash
    source_sha256_after = $stage6headrefAfterHash
    source_unchanged = ($stage6headrefAfterHash -eq $stage6headrefExpectedHash)
    source_read_only = $stage6headrefAfterInfo.IsReadOnly
    source_bytes = $stage6headrefAfterInfo.Length
    other_processes_stopped = $false
}
$stage6headrefRun | ConvertTo-Json | Set-Content -LiteralPath $stage6headrefRecord -Encoding utf8
$stage6headrefRun | ConvertTo-Json
Get-Content -LiteralPath $stage6headrefStdout -Tail 4
Get-Content -LiteralPath $stage6headrefStderr -Tail 4
if ($stage6headrefStopReason -or $stage6headrefMonitorError -or $stage6headrefCleanupError -or -not $stage6headrefExitConfirmed -or $stage6headrefExitCode -ne 0 -or -not $stage6headrefRun.source_unchanged) { exit 1 }
