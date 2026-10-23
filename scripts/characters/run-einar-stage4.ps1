param([ValidateSet('stage4', 'stage4r1')][string]$RunRecord = 'stage4')
$ErrorActionPreference = 'Stop'
$stage4Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$stage4Qa = Join-Path $stage4Root 'qa/characters/plato/v002/einar-intake'
$stage4Stdout = Join-Path $stage4Qa ($RunRecord + '.stdout.log')
$stage4Stderr = Join-Path $stage4Qa ($RunRecord + '.stderr.log')
$stage4Record = Join-Path $stage4Qa ($RunRecord + '-run.json')
$stage4Source = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/project-management/source-cache/einar-v1/extracted/einar_release_v1.blend'
$stage4Exe = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/production/.tools/blender/blender-4.5.15-windows-x64/blender.exe'
$stage4ExpectedHash = '1c6663da0a2e9d6822978467c244e9186edc76083bae2414e02f9e695e711f7b'
$stage4SourceInfo = Get-Item -LiteralPath $stage4Source
$stage4BeforeHash = (Get-FileHash -LiteralPath $stage4Source -Algorithm SHA256).Hash.ToLowerInvariant()
if ($stage4BeforeHash -ne $stage4ExpectedHash -or $stage4SourceInfo.Length -ne 91323760 -or -not $stage4SourceInfo.IsReadOnly) {
    throw 'Approved read-only source preflight mismatch'
}
New-Item -ItemType Directory -Path $stage4Qa -Force | Out-Null
if (Test-Path -LiteralPath $stage4Record) { throw 'Preserve previous invocation record; do not retry implicitly' }
$stage4Args = @('--background', '--factory-startup', '--disable-autoexec', '--threads', '4', '--python-exit-code', '1', '--python', (Join-Path $PSScriptRoot 'inspect-einar-modifiers.py'))
$stage4Clock = [Diagnostics.Stopwatch]::StartNew()
$stage4Process = Start-Process -FilePath $stage4Exe -ArgumentList $stage4Args -WorkingDirectory $stage4Root -WindowStyle Hidden -RedirectStandardOutput $stage4Stdout -RedirectStandardError $stage4Stderr -PassThru
$stage4OwnedPid = $stage4Process.Id
$stage4LimitBytes = [int64](1.2 * 1GB)
$stage4PeakSampled = [int64]0
$stage4PeakReported = [int64]0
$stage4StopReason = $null
$stage4MonitorError = $null
$stage4CleanupError = $null
$stage4ExitConfirmed = $false
try {
    while (-not $stage4Process.HasExited) {
        $stage4Process.Refresh()
        if ($stage4Process.HasExited) { break }
        $stage4PeakSampled = [math]::Max($stage4PeakSampled, $stage4Process.WorkingSet64)
        $stage4PeakReported = [math]::Max($stage4PeakReported, $stage4Process.PeakWorkingSet64)
        if ($stage4Process.WorkingSet64 -gt $stage4LimitBytes -or $stage4Process.PeakWorkingSet64 -gt $stage4LimitBytes) {
            $stage4StopReason = 'working_set_limit_1_2_GiB'
        } elseif ($stage4Clock.Elapsed.TotalSeconds -ge 45) {
            $stage4StopReason = 'timeout_45_seconds'
        }
        if ($null -ne $stage4StopReason) { break }
        Start-Sleep -Milliseconds 100
    }
} catch {
    $stage4MonitorError = $_.Exception.Message
    $stage4StopReason = 'monitor_exception'
} finally {
    try {
        # This is the Process handle returned by this exact Start-Process call.
        # Never enumerate/stop another Blender, user P0, Unity or any other app.
        if (-not $stage4Process.HasExited) {
            if (-not $stage4StopReason) { $stage4StopReason = 'unexpected_monitor_exit' }
            $stage4Process.Kill()
        }
        $stage4ExitConfirmed = $stage4Process.WaitForExit(5000)
    } catch {
        $stage4CleanupError = $_.Exception.Message
    }
    $stage4Clock.Stop()
}
$stage4ExitCode = if ($stage4ExitConfirmed) { $stage4Process.ExitCode } else { $null }
$stage4AfterHash = (Get-FileHash -LiteralPath $stage4Source -Algorithm SHA256).Hash.ToLowerInvariant()
$stage4AfterInfo = Get-Item -LiteralPath $stage4Source
$stage4Run = [ordered]@{
    owned_blender_pid = $stage4OwnedPid
    process_exit_code = $stage4ExitCode
    process_exit_confirmed = $stage4ExitConfirmed
    monitor_error = $stage4MonitorError
    cleanup_error = $stage4CleanupError
    process_wall_seconds = [math]::Round($stage4Clock.Elapsed.TotalSeconds, 3)
    maximum_seconds = 45
    working_set_limit_bytes = $stage4LimitBytes
    peak_sampled_working_set_mib = [math]::Round($stage4PeakSampled / 1MB, 2)
    peak_OS_working_set_mib = [math]::Round($stage4PeakReported / 1MB, 2)
    stopped_for_limit = $stage4StopReason
    source_sha256_before = $stage4BeforeHash
    source_sha256_after = $stage4AfterHash
    source_unchanged = ($stage4AfterHash -eq $stage4ExpectedHash)
    source_read_only = $stage4AfterInfo.IsReadOnly
    source_bytes = $stage4AfterInfo.Length
    other_processes_stopped = $false
}
$stage4Run | ConvertTo-Json | Set-Content -LiteralPath $stage4Record -Encoding utf8
$stage4Run | ConvertTo-Json
Get-Content -LiteralPath $stage4Stdout -Tail 4
Get-Content -LiteralPath $stage4Stderr -Tail 4
if ($stage4StopReason -or $stage4MonitorError -or $stage4CleanupError -or -not $stage4ExitConfirmed -or $stage4ExitCode -ne 0 -or -not $stage4Run.source_unchanged) { exit 1 }
