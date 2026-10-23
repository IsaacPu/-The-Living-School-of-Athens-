param([ValidateSet('stage7occlusion', 'stage7occlusionr1')][string]$RunRecord = 'stage7occlusion')
$ErrorActionPreference = 'Stop'
$stage7occlusionRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$stage7occlusionQa = Join-Path $stage7occlusionRoot 'qa/characters/plato/v002/einar-intake'
$stage7occlusionStdout = Join-Path $stage7occlusionQa ($RunRecord + '.stdout.log')
$stage7occlusionStderr = Join-Path $stage7occlusionQa ($RunRecord + '.stderr.log')
$stage7occlusionRecord = Join-Path $stage7occlusionQa ($RunRecord + '-run.json')
$stage7occlusionSource = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/project-management/source-cache/einar-v1/extracted/einar_release_v1.blend'
$stage7occlusionExe = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/production/.tools/blender/blender-4.5.15-windows-x64/blender.exe'
$stage7occlusionExpectedHash = '1c6663da0a2e9d6822978467c244e9186edc76083bae2414e02f9e695e711f7b'
$stage7occlusionSourceInfo = Get-Item -LiteralPath $stage7occlusionSource
$stage7occlusionBeforeHash = (Get-FileHash -LiteralPath $stage7occlusionSource -Algorithm SHA256).Hash.ToLowerInvariant()
if ($stage7occlusionBeforeHash -ne $stage7occlusionExpectedHash -or $stage7occlusionSourceInfo.Length -ne 91323760 -or -not $stage7occlusionSourceInfo.IsReadOnly) {
    throw 'Approved read-only source preflight mismatch'
}
New-Item -ItemType Directory -Path $stage7occlusionQa -Force | Out-Null
if (Test-Path -LiteralPath $stage7occlusionRecord) { throw 'Preserve previous invocation record; do not retry implicitly' }
$stage7occlusionArgs = @('--background', '--factory-startup', '--disable-autoexec', '--threads', '4', '--python-exit-code', '1', '--python', (Join-Path $PSScriptRoot 'diagnose-einar-eye-occlusion.py'))
$stage7occlusionClock = [Diagnostics.Stopwatch]::StartNew()
$stage7occlusionProcess = Start-Process -FilePath $stage7occlusionExe -ArgumentList $stage7occlusionArgs -WorkingDirectory $stage7occlusionRoot -WindowStyle Hidden -RedirectStandardOutput $stage7occlusionStdout -RedirectStandardError $stage7occlusionStderr -PassThru
$stage7occlusionOwnedPid = $stage7occlusionProcess.Id
$stage7occlusionLimitBytes = [int64](1.2 * 1GB)
$stage7occlusionPeakSampled = [int64]0
$stage7occlusionPeakReported = [int64]0
$stage7occlusionStopReason = $null
$stage7occlusionMonitorError = $null
$stage7occlusionCleanupError = $null
$stage7occlusionExitConfirmed = $false
try {
    while (-not $stage7occlusionProcess.HasExited) {
        $stage7occlusionProcess.Refresh()
        if ($stage7occlusionProcess.HasExited) { break }
        $stage7occlusionPeakSampled = [math]::Max($stage7occlusionPeakSampled, $stage7occlusionProcess.WorkingSet64)
        $stage7occlusionPeakReported = [math]::Max($stage7occlusionPeakReported, $stage7occlusionProcess.PeakWorkingSet64)
        if ($stage7occlusionProcess.WorkingSet64 -gt $stage7occlusionLimitBytes -or $stage7occlusionProcess.PeakWorkingSet64 -gt $stage7occlusionLimitBytes) {
            $stage7occlusionStopReason = 'working_set_limit_1_2_GiB'
        } elseif ($stage7occlusionClock.Elapsed.TotalSeconds -ge 45) {
            $stage7occlusionStopReason = 'timeout_45_seconds'
        }
        if ($null -ne $stage7occlusionStopReason) { break }
        Start-Sleep -Milliseconds 100
    }
} catch {
    $stage7occlusionMonitorError = $_.Exception.Message
    $stage7occlusionStopReason = 'monitor_exception'
} finally {
    try {
        # This is the Process handle returned by this exact Start-Process call.
        # Never enumerate/stop another Blender, user P0, Unity or any other app.
        if (-not $stage7occlusionProcess.HasExited) {
            if (-not $stage7occlusionStopReason) { $stage7occlusionStopReason = 'unexpected_monitor_exit' }
            $stage7occlusionProcess.Kill()
        }
        $stage7occlusionExitConfirmed = $stage7occlusionProcess.WaitForExit(5000)
    } catch {
        $stage7occlusionCleanupError = $_.Exception.Message
    }
    $stage7occlusionClock.Stop()
}
$stage7occlusionExitCode = if ($stage7occlusionExitConfirmed) { $stage7occlusionProcess.ExitCode } else { $null }
$stage7occlusionAfterHash = (Get-FileHash -LiteralPath $stage7occlusionSource -Algorithm SHA256).Hash.ToLowerInvariant()
$stage7occlusionAfterInfo = Get-Item -LiteralPath $stage7occlusionSource
$stage7occlusionRun = [ordered]@{
    owned_blender_pid = $stage7occlusionOwnedPid
    process_exit_code = $stage7occlusionExitCode
    process_exit_confirmed = $stage7occlusionExitConfirmed
    monitor_error = $stage7occlusionMonitorError
    cleanup_error = $stage7occlusionCleanupError
    process_wall_seconds = [math]::Round($stage7occlusionClock.Elapsed.TotalSeconds, 3)
    maximum_seconds = 45
    working_set_limit_bytes = $stage7occlusionLimitBytes
    peak_sampled_working_set_mib = [math]::Round($stage7occlusionPeakSampled / 1MB, 2)
    peak_OS_working_set_mib = [math]::Round($stage7occlusionPeakReported / 1MB, 2)
    stopped_for_limit = $stage7occlusionStopReason
    source_sha256_before = $stage7occlusionBeforeHash
    source_sha256_after = $stage7occlusionAfterHash
    source_unchanged = ($stage7occlusionAfterHash -eq $stage7occlusionExpectedHash)
    source_read_only = $stage7occlusionAfterInfo.IsReadOnly
    source_bytes = $stage7occlusionAfterInfo.Length
    other_processes_stopped = $false
}
$stage7occlusionRun | ConvertTo-Json | Set-Content -LiteralPath $stage7occlusionRecord -Encoding utf8
$stage7occlusionRun | ConvertTo-Json
Get-Content -LiteralPath $stage7occlusionStdout -Tail 4
Get-Content -LiteralPath $stage7occlusionStderr -Tail 4
if ($stage7occlusionStopReason -or $stage7occlusionMonitorError -or $stage7occlusionCleanupError -or -not $stage7occlusionExitConfirmed -or $stage7occlusionExitCode -ne 0 -or -not $stage7occlusionRun.source_unchanged) { exit 1 }
