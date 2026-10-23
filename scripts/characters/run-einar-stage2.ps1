$ErrorActionPreference = 'Stop'
$stage2Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$stage2Qa = Join-Path $stage2Root 'qa/characters/plato/v002/einar-intake'
$stage2Source = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/project-management/source-cache/einar-v1/extracted/einar_release_v1.blend'
$stage2Exe = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/production/.tools/blender/blender-4.5.15-windows-x64/blender.exe'
$stage2ExpectedHash = '1c6663da0a2e9d6822978467c244e9186edc76083bae2414e02f9e695e711f7b'
$stage2SourceInfo = Get-Item -LiteralPath $stage2Source
$stage2BeforeHash = (Get-FileHash -LiteralPath $stage2Source -Algorithm SHA256).Hash.ToLowerInvariant()
if ($stage2BeforeHash -ne $stage2ExpectedHash -or $stage2SourceInfo.Length -ne 91323760 -or -not $stage2SourceInfo.IsReadOnly) {
    throw 'Approved read-only source preflight mismatch'
}
New-Item -ItemType Directory -Path $stage2Qa -Force | Out-Null
if (Test-Path -LiteralPath (Join-Path $stage2Qa 'stage2-run.json')) { throw 'Preserve previous stage2 invocation record; do not retry implicitly' }
$stage2Args = @('--background', '--factory-startup', '--disable-autoexec', '--threads', '4', '--python-exit-code', '1', '--python', (Join-Path $PSScriptRoot 'preview-einar-clean-base.py'))
$stage2Clock = [Diagnostics.Stopwatch]::StartNew()
$stage2Process = Start-Process -FilePath $stage2Exe -ArgumentList $stage2Args -WorkingDirectory $stage2Root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $stage2Qa 'stage2.stdout.log') -RedirectStandardError (Join-Path $stage2Qa 'stage2.stderr.log') -PassThru
$stage2OwnedPid = $stage2Process.Id
$stage2LimitBytes = [int64](1.2 * 1GB)
$stage2PeakSampled = [int64]0
$stage2PeakReported = [int64]0
$stage2StopReason = $null
$stage2MonitorError = $null
$stage2CleanupError = $null
$stage2ExitConfirmed = $false
try {
    while (-not $stage2Process.HasExited) {
        $stage2Process.Refresh()
        if ($stage2Process.HasExited) { break }
        $stage2PeakSampled = [math]::Max($stage2PeakSampled, $stage2Process.WorkingSet64)
        $stage2PeakReported = [math]::Max($stage2PeakReported, $stage2Process.PeakWorkingSet64)
        if ($stage2Process.WorkingSet64 -gt $stage2LimitBytes -or $stage2Process.PeakWorkingSet64 -gt $stage2LimitBytes) {
            $stage2StopReason = 'working_set_limit_1_2_GiB'
        } elseif ($stage2Clock.Elapsed.TotalSeconds -ge 45) {
            $stage2StopReason = 'timeout_45_seconds'
        }
        if ($null -ne $stage2StopReason) { break }
        Start-Sleep -Milliseconds 100
    }
} catch {
    $stage2MonitorError = $_.Exception.Message
    $stage2StopReason = 'monitor_exception'
} finally {
    try {
        # This is the Process handle returned by this exact Start-Process call.
        # Never enumerate/stop another Blender, user P0, Unity or any other app.
        if (-not $stage2Process.HasExited) {
            if (-not $stage2StopReason) { $stage2StopReason = 'unexpected_monitor_exit' }
            $stage2Process.Kill()
        }
        $stage2ExitConfirmed = $stage2Process.WaitForExit(5000)
    } catch {
        $stage2CleanupError = $_.Exception.Message
    }
    $stage2Clock.Stop()
}
$stage2ExitCode = if ($stage2ExitConfirmed) { $stage2Process.ExitCode } else { $null }
$stage2AfterHash = (Get-FileHash -LiteralPath $stage2Source -Algorithm SHA256).Hash.ToLowerInvariant()
$stage2AfterInfo = Get-Item -LiteralPath $stage2Source
$stage2Run = [ordered]@{
    owned_blender_pid = $stage2OwnedPid
    process_exit_code = $stage2ExitCode
    process_exit_confirmed = $stage2ExitConfirmed
    monitor_error = $stage2MonitorError
    cleanup_error = $stage2CleanupError
    process_wall_seconds = [math]::Round($stage2Clock.Elapsed.TotalSeconds, 3)
    maximum_seconds = 45
    working_set_limit_bytes = $stage2LimitBytes
    peak_sampled_working_set_mib = [math]::Round($stage2PeakSampled / 1MB, 2)
    peak_OS_working_set_mib = [math]::Round($stage2PeakReported / 1MB, 2)
    stopped_for_limit = $stage2StopReason
    source_sha256_before = $stage2BeforeHash
    source_sha256_after = $stage2AfterHash
    source_unchanged = ($stage2AfterHash -eq $stage2ExpectedHash)
    source_read_only = $stage2AfterInfo.IsReadOnly
    source_bytes = $stage2AfterInfo.Length
    other_processes_stopped = $false
}
$stage2Run | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $stage2Qa 'stage2-run.json') -Encoding utf8
$stage2Run | ConvertTo-Json
Get-Content -LiteralPath (Join-Path $stage2Qa 'stage2.stdout.log') -Tail 4
Get-Content -LiteralPath (Join-Path $stage2Qa 'stage2.stderr.log') -Tail 4
if ($stage2StopReason -or $stage2MonitorError -or $stage2CleanupError -or -not $stage2ExitConfirmed -or $stage2ExitCode -ne 0 -or -not $stage2Run.source_unchanged) { exit 1 }
