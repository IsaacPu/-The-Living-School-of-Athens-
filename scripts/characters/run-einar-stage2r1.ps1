$ErrorActionPreference = 'Stop'
$stage2r1Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$stage2r1Qa = Join-Path $stage2r1Root 'qa/characters/plato/v002/einar-intake'
$stage2r1Source = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/project-management/source-cache/einar-v1/extracted/einar_release_v1.blend'
$stage2r1Exe = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/production/.tools/blender/blender-4.5.15-windows-x64/blender.exe'
$stage2r1ExpectedHash = '1c6663da0a2e9d6822978467c244e9186edc76083bae2414e02f9e695e711f7b'
$stage2r1SourceInfo = Get-Item -LiteralPath $stage2r1Source
$stage2r1BeforeHash = (Get-FileHash -LiteralPath $stage2r1Source -Algorithm SHA256).Hash.ToLowerInvariant()
if ($stage2r1BeforeHash -ne $stage2r1ExpectedHash -or $stage2r1SourceInfo.Length -ne 91323760 -or -not $stage2r1SourceInfo.IsReadOnly) {
    throw 'Approved read-only source preflight mismatch'
}
New-Item -ItemType Directory -Path $stage2r1Qa -Force | Out-Null
if (Test-Path -LiteralPath (Join-Path $stage2r1Qa 'stage2r1-run.json')) { throw 'Preserve previous stage2r1 invocation record; do not retry implicitly' }
$stage2r1Args = @('--background', '--factory-startup', '--disable-autoexec', '--threads', '4', '--python-exit-code', '1', '--python', (Join-Path $PSScriptRoot 'preview-einar-clean-base.py'))
$stage2r1Clock = [Diagnostics.Stopwatch]::StartNew()
$stage2r1Process = Start-Process -FilePath $stage2r1Exe -ArgumentList $stage2r1Args -WorkingDirectory $stage2r1Root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $stage2r1Qa 'stage2r1.stdout.log') -RedirectStandardError (Join-Path $stage2r1Qa 'stage2r1.stderr.log') -PassThru
$stage2r1OwnedPid = $stage2r1Process.Id
$stage2r1LimitBytes = [int64](1.2 * 1GB)
$stage2r1PeakSampled = [int64]0
$stage2r1PeakReported = [int64]0
$stage2r1StopReason = $null
$stage2r1MonitorError = $null
$stage2r1CleanupError = $null
$stage2r1ExitConfirmed = $false
try {
    while (-not $stage2r1Process.HasExited) {
        $stage2r1Process.Refresh()
        if ($stage2r1Process.HasExited) { break }
        $stage2r1PeakSampled = [math]::Max($stage2r1PeakSampled, $stage2r1Process.WorkingSet64)
        $stage2r1PeakReported = [math]::Max($stage2r1PeakReported, $stage2r1Process.PeakWorkingSet64)
        if ($stage2r1Process.WorkingSet64 -gt $stage2r1LimitBytes -or $stage2r1Process.PeakWorkingSet64 -gt $stage2r1LimitBytes) {
            $stage2r1StopReason = 'working_set_limit_1_2_GiB'
        } elseif ($stage2r1Clock.Elapsed.TotalSeconds -ge 45) {
            $stage2r1StopReason = 'timeout_45_seconds'
        }
        if ($null -ne $stage2r1StopReason) { break }
        Start-Sleep -Milliseconds 100
    }
} catch {
    $stage2r1MonitorError = $_.Exception.Message
    $stage2r1StopReason = 'monitor_exception'
} finally {
    try {
        # This is the Process handle returned by this exact Start-Process call.
        # Never enumerate/stop another Blender, user P0, Unity or any other app.
        if (-not $stage2r1Process.HasExited) {
            if (-not $stage2r1StopReason) { $stage2r1StopReason = 'unexpected_monitor_exit' }
            $stage2r1Process.Kill()
        }
        $stage2r1ExitConfirmed = $stage2r1Process.WaitForExit(5000)
    } catch {
        $stage2r1CleanupError = $_.Exception.Message
    }
    $stage2r1Clock.Stop()
}
$stage2r1ExitCode = if ($stage2r1ExitConfirmed) { $stage2r1Process.ExitCode } else { $null }
$stage2r1AfterHash = (Get-FileHash -LiteralPath $stage2r1Source -Algorithm SHA256).Hash.ToLowerInvariant()
$stage2r1AfterInfo = Get-Item -LiteralPath $stage2r1Source
$stage2r1Run = [ordered]@{
    owned_blender_pid = $stage2r1OwnedPid
    process_exit_code = $stage2r1ExitCode
    process_exit_confirmed = $stage2r1ExitConfirmed
    monitor_error = $stage2r1MonitorError
    cleanup_error = $stage2r1CleanupError
    process_wall_seconds = [math]::Round($stage2r1Clock.Elapsed.TotalSeconds, 3)
    maximum_seconds = 45
    working_set_limit_bytes = $stage2r1LimitBytes
    peak_sampled_working_set_mib = [math]::Round($stage2r1PeakSampled / 1MB, 2)
    peak_OS_working_set_mib = [math]::Round($stage2r1PeakReported / 1MB, 2)
    stopped_for_limit = $stage2r1StopReason
    source_sha256_before = $stage2r1BeforeHash
    source_sha256_after = $stage2r1AfterHash
    source_unchanged = ($stage2r1AfterHash -eq $stage2r1ExpectedHash)
    source_read_only = $stage2r1AfterInfo.IsReadOnly
    source_bytes = $stage2r1AfterInfo.Length
    other_processes_stopped = $false
}
$stage2r1Run | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $stage2r1Qa 'stage2r1-run.json') -Encoding utf8
$stage2r1Run | ConvertTo-Json
Get-Content -LiteralPath (Join-Path $stage2r1Qa 'stage2r1.stdout.log') -Tail 4
Get-Content -LiteralPath (Join-Path $stage2r1Qa 'stage2r1.stderr.log') -Tail 4
if ($stage2r1StopReason -or $stage2r1MonitorError -or $stage2r1CleanupError -or -not $stage2r1ExitConfirmed -or $stage2r1ExitCode -ne 0 -or -not $stage2r1Run.source_unchanged) { exit 1 }
