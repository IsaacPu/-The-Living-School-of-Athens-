param([ValidateSet('stage4nodes', 'stage4nodesr1')][string]$RunRecord = 'stage4nodes')
$ErrorActionPreference = 'Stop'
$stage4nodesRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$stage4nodesQa = Join-Path $stage4nodesRoot 'qa/characters/plato/v002/einar-intake'
$stage4nodesStdout = Join-Path $stage4nodesQa ($RunRecord + '.stdout.log')
$stage4nodesStderr = Join-Path $stage4nodesQa ($RunRecord + '.stderr.log')
$stage4nodesRecord = Join-Path $stage4nodesQa ($RunRecord + '-run.json')
$stage4nodesSource = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/project-management/source-cache/einar-v1/extracted/einar_release_v1.blend'
$stage4nodesExe = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/production/.tools/blender/blender-4.5.15-windows-x64/blender.exe'
$stage4nodesExpectedHash = '1c6663da0a2e9d6822978467c244e9186edc76083bae2414e02f9e695e711f7b'
$stage4nodesSourceInfo = Get-Item -LiteralPath $stage4nodesSource
$stage4nodesBeforeHash = (Get-FileHash -LiteralPath $stage4nodesSource -Algorithm SHA256).Hash.ToLowerInvariant()
if ($stage4nodesBeforeHash -ne $stage4nodesExpectedHash -or $stage4nodesSourceInfo.Length -ne 91323760 -or -not $stage4nodesSourceInfo.IsReadOnly) {
    throw 'Approved read-only source preflight mismatch'
}
New-Item -ItemType Directory -Path $stage4nodesQa -Force | Out-Null
if (Test-Path -LiteralPath $stage4nodesRecord) { throw 'Preserve previous invocation record; do not retry implicitly' }
$stage4nodesArgs = @('--background', '--factory-startup', '--disable-autoexec', '--threads', '4', '--python-exit-code', '1', '--python', (Join-Path $PSScriptRoot 'inspect-einar-geometry-nodes.py'))
$stage4nodesClock = [Diagnostics.Stopwatch]::StartNew()
$stage4nodesProcess = Start-Process -FilePath $stage4nodesExe -ArgumentList $stage4nodesArgs -WorkingDirectory $stage4nodesRoot -WindowStyle Hidden -RedirectStandardOutput $stage4nodesStdout -RedirectStandardError $stage4nodesStderr -PassThru
$stage4nodesOwnedPid = $stage4nodesProcess.Id
$stage4nodesLimitBytes = [int64](1.2 * 1GB)
$stage4nodesPeakSampled = [int64]0
$stage4nodesPeakReported = [int64]0
$stage4nodesStopReason = $null
$stage4nodesMonitorError = $null
$stage4nodesCleanupError = $null
$stage4nodesExitConfirmed = $false
try {
    while (-not $stage4nodesProcess.HasExited) {
        $stage4nodesProcess.Refresh()
        if ($stage4nodesProcess.HasExited) { break }
        $stage4nodesPeakSampled = [math]::Max($stage4nodesPeakSampled, $stage4nodesProcess.WorkingSet64)
        $stage4nodesPeakReported = [math]::Max($stage4nodesPeakReported, $stage4nodesProcess.PeakWorkingSet64)
        if ($stage4nodesProcess.WorkingSet64 -gt $stage4nodesLimitBytes -or $stage4nodesProcess.PeakWorkingSet64 -gt $stage4nodesLimitBytes) {
            $stage4nodesStopReason = 'working_set_limit_1_2_GiB'
        } elseif ($stage4nodesClock.Elapsed.TotalSeconds -ge 45) {
            $stage4nodesStopReason = 'timeout_45_seconds'
        }
        if ($null -ne $stage4nodesStopReason) { break }
        Start-Sleep -Milliseconds 100
    }
} catch {
    $stage4nodesMonitorError = $_.Exception.Message
    $stage4nodesStopReason = 'monitor_exception'
} finally {
    try {
        # This is the Process handle returned by this exact Start-Process call.
        # Never enumerate/stop another Blender, user P0, Unity or any other app.
        if (-not $stage4nodesProcess.HasExited) {
            if (-not $stage4nodesStopReason) { $stage4nodesStopReason = 'unexpected_monitor_exit' }
            $stage4nodesProcess.Kill()
        }
        $stage4nodesExitConfirmed = $stage4nodesProcess.WaitForExit(5000)
    } catch {
        $stage4nodesCleanupError = $_.Exception.Message
    }
    $stage4nodesClock.Stop()
}
$stage4nodesExitCode = if ($stage4nodesExitConfirmed) { $stage4nodesProcess.ExitCode } else { $null }
$stage4nodesAfterHash = (Get-FileHash -LiteralPath $stage4nodesSource -Algorithm SHA256).Hash.ToLowerInvariant()
$stage4nodesAfterInfo = Get-Item -LiteralPath $stage4nodesSource
$stage4nodesRun = [ordered]@{
    owned_blender_pid = $stage4nodesOwnedPid
    process_exit_code = $stage4nodesExitCode
    process_exit_confirmed = $stage4nodesExitConfirmed
    monitor_error = $stage4nodesMonitorError
    cleanup_error = $stage4nodesCleanupError
    process_wall_seconds = [math]::Round($stage4nodesClock.Elapsed.TotalSeconds, 3)
    maximum_seconds = 45
    working_set_limit_bytes = $stage4nodesLimitBytes
    peak_sampled_working_set_mib = [math]::Round($stage4nodesPeakSampled / 1MB, 2)
    peak_OS_working_set_mib = [math]::Round($stage4nodesPeakReported / 1MB, 2)
    stopped_for_limit = $stage4nodesStopReason
    source_sha256_before = $stage4nodesBeforeHash
    source_sha256_after = $stage4nodesAfterHash
    source_unchanged = ($stage4nodesAfterHash -eq $stage4nodesExpectedHash)
    source_read_only = $stage4nodesAfterInfo.IsReadOnly
    source_bytes = $stage4nodesAfterInfo.Length
    other_processes_stopped = $false
}
$stage4nodesRun | ConvertTo-Json | Set-Content -LiteralPath $stage4nodesRecord -Encoding utf8
$stage4nodesRun | ConvertTo-Json
Get-Content -LiteralPath $stage4nodesStdout -Tail 4
Get-Content -LiteralPath $stage4nodesStderr -Tail 4
if ($stage4nodesStopReason -or $stage4nodesMonitorError -or $stage4nodesCleanupError -or -not $stage4nodesExitConfirmed -or $stage4nodesExitCode -ne 0 -or -not $stage4nodesRun.source_unchanged) { exit 1 }
