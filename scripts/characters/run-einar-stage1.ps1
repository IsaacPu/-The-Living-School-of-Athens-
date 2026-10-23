$ErrorActionPreference = 'Stop'
$stage1Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$stage1Qa = Join-Path $stage1Root 'qa/characters/plato/v002/einar-intake'
$stage1Source = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/project-management/source-cache/einar-v1/extracted/einar_release_v1.blend'
$stage1Exe = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/production/.tools/blender/blender-4.5.15-windows-x64/blender.exe'
$stage1ExpectedHash = '1c6663da0a2e9d6822978467c244e9186edc76083bae2414e02f9e695e711f7b'
$stage1SourceInfo = Get-Item -LiteralPath $stage1Source
$stage1BeforeHash = (Get-FileHash -LiteralPath $stage1Source -Algorithm SHA256).Hash.ToLowerInvariant()
if ($stage1BeforeHash -ne $stage1ExpectedHash -or $stage1SourceInfo.Length -ne 91323760 -or -not $stage1SourceInfo.IsReadOnly) {
    throw 'Approved read-only source preflight mismatch'
}
New-Item -ItemType Directory -Path $stage1Qa -Force | Out-Null
if (Test-Path -LiteralPath (Join-Path $stage1Qa 'stage1-run.json')) { throw 'Preserve previous stage1 invocation record; do not retry implicitly' }
$stage1Args = @('--background', '--factory-startup', '--disable-autoexec', '--threads', '4', '--python-exit-code', '1', '--python', (Join-Path $PSScriptRoot 'inspect-einar-raw-meshes.py'))
$stage1Clock = [Diagnostics.Stopwatch]::StartNew()
$stage1Process = Start-Process -FilePath $stage1Exe -ArgumentList $stage1Args -WorkingDirectory $stage1Root -WindowStyle Hidden -RedirectStandardOutput (Join-Path $stage1Qa 'stage1.stdout.log') -RedirectStandardError (Join-Path $stage1Qa 'stage1.stderr.log') -PassThru
$stage1OwnedPid = $stage1Process.Id
$stage1LimitBytes = [int64](1.2 * 1GB)
$stage1PeakSampled = [int64]0
$stage1PeakReported = [int64]0
$stage1StopReason = $null
$stage1MonitorError = $null
$stage1CleanupError = $null
$stage1ExitConfirmed = $false
try {
    while (-not $stage1Process.HasExited) {
        $stage1Process.Refresh()
        if ($stage1Process.HasExited) { break }
        $stage1PeakSampled = [math]::Max($stage1PeakSampled, $stage1Process.WorkingSet64)
        $stage1PeakReported = [math]::Max($stage1PeakReported, $stage1Process.PeakWorkingSet64)
        if ($stage1Process.WorkingSet64 -gt $stage1LimitBytes -or $stage1Process.PeakWorkingSet64 -gt $stage1LimitBytes) {
            $stage1StopReason = 'working_set_limit_1_2_GiB'
        } elseif ($stage1Clock.Elapsed.TotalSeconds -ge 45) {
            $stage1StopReason = 'timeout_45_seconds'
        }
        if ($null -ne $stage1StopReason) { break }
        Start-Sleep -Milliseconds 100
    }
} catch {
    $stage1MonitorError = $_.Exception.Message
    $stage1StopReason = 'monitor_exception'
} finally {
    try {
        # This is the Process handle returned by this exact Start-Process call.
        # Never enumerate/stop another Blender, user P0, Unity or any other app.
        if (-not $stage1Process.HasExited) {
            if (-not $stage1StopReason) { $stage1StopReason = 'unexpected_monitor_exit' }
            $stage1Process.Kill()
        }
        $stage1ExitConfirmed = $stage1Process.WaitForExit(5000)
    } catch {
        $stage1CleanupError = $_.Exception.Message
    }
    $stage1Clock.Stop()
}
$stage1ExitCode = if ($stage1ExitConfirmed) { $stage1Process.ExitCode } else { $null }
$stage1AfterHash = (Get-FileHash -LiteralPath $stage1Source -Algorithm SHA256).Hash.ToLowerInvariant()
$stage1AfterInfo = Get-Item -LiteralPath $stage1Source
$stage1Run = [ordered]@{
    owned_blender_pid = $stage1OwnedPid
    process_exit_code = $stage1ExitCode
    process_exit_confirmed = $stage1ExitConfirmed
    monitor_error = $stage1MonitorError
    cleanup_error = $stage1CleanupError
    process_wall_seconds = [math]::Round($stage1Clock.Elapsed.TotalSeconds, 3)
    maximum_seconds = 45
    working_set_limit_bytes = $stage1LimitBytes
    peak_sampled_working_set_mib = [math]::Round($stage1PeakSampled / 1MB, 2)
    peak_OS_working_set_mib = [math]::Round($stage1PeakReported / 1MB, 2)
    stopped_for_limit = $stage1StopReason
    source_sha256_before = $stage1BeforeHash
    source_sha256_after = $stage1AfterHash
    source_unchanged = ($stage1AfterHash -eq $stage1ExpectedHash)
    source_read_only = $stage1AfterInfo.IsReadOnly
    source_bytes = $stage1AfterInfo.Length
    other_processes_stopped = $false
}
$stage1Run | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $stage1Qa 'stage1-run.json') -Encoding utf8
$stage1Run | ConvertTo-Json
Get-Content -LiteralPath (Join-Path $stage1Qa 'stage1.stdout.log') -Tail 4
Get-Content -LiteralPath (Join-Path $stage1Qa 'stage1.stderr.log') -Tail 4
if ($stage1StopReason -or $stage1MonitorError -or $stage1CleanupError -or -not $stage1ExitConfirmed -or $stage1ExitCode -ne 0 -or -not $stage1Run.source_unchanged) { exit 1 }
