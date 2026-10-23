param([ValidateSet('stage7', 'stage7r1')][string]$RunRecord = 'stage7')
$ErrorActionPreference = 'Stop'
$stage7Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$stage7Qa = Join-Path $stage7Root 'qa/characters/plato/v002/einar-intake'
$stage7Stdout = Join-Path $stage7Qa ($RunRecord + '.stdout.log')
$stage7Stderr = Join-Path $stage7Qa ($RunRecord + '.stderr.log')
$stage7Record = Join-Path $stage7Qa ($RunRecord + '-run.json')
$stage7Source = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/project-management/source-cache/einar-v1/extracted/einar_release_v1.blend'
$stage7Exe = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/production/.tools/blender/blender-4.5.15-windows-x64/blender.exe'
$stage7ExpectedHash = '1c6663da0a2e9d6822978467c244e9186edc76083bae2414e02f9e695e711f7b'
$stage7SourceInfo = Get-Item -LiteralPath $stage7Source
$stage7BeforeHash = (Get-FileHash -LiteralPath $stage7Source -Algorithm SHA256).Hash.ToLowerInvariant()
if ($stage7BeforeHash -ne $stage7ExpectedHash -or $stage7SourceInfo.Length -ne 91323760 -or -not $stage7SourceInfo.IsReadOnly) {
    throw 'Approved read-only source preflight mismatch'
}
New-Item -ItemType Directory -Path $stage7Qa -Force | Out-Null
if (Test-Path -LiteralPath $stage7Record) { throw 'Preserve previous invocation record; do not retry implicitly' }
$stage7Args = @('--background', '--factory-startup', '--disable-autoexec', '--threads', '4', '--python-exit-code', '1', '--python', (Join-Path $PSScriptRoot 'render-einar-static-closeup.py'))
$stage7Clock = [Diagnostics.Stopwatch]::StartNew()
$stage7Process = Start-Process -FilePath $stage7Exe -ArgumentList $stage7Args -WorkingDirectory $stage7Root -WindowStyle Hidden -RedirectStandardOutput $stage7Stdout -RedirectStandardError $stage7Stderr -PassThru
$stage7OwnedPid = $stage7Process.Id
$stage7LimitBytes = [int64](1.2 * 1GB)
$stage7PeakSampled = [int64]0
$stage7PeakReported = [int64]0
$stage7StopReason = $null
$stage7MonitorError = $null
$stage7CleanupError = $null
$stage7ExitConfirmed = $false
try {
    while (-not $stage7Process.HasExited) {
        $stage7Process.Refresh()
        if ($stage7Process.HasExited) { break }
        $stage7PeakSampled = [math]::Max($stage7PeakSampled, $stage7Process.WorkingSet64)
        $stage7PeakReported = [math]::Max($stage7PeakReported, $stage7Process.PeakWorkingSet64)
        if ($stage7Process.WorkingSet64 -gt $stage7LimitBytes -or $stage7Process.PeakWorkingSet64 -gt $stage7LimitBytes) {
            $stage7StopReason = 'working_set_limit_1_2_GiB'
        } elseif ($stage7Clock.Elapsed.TotalSeconds -ge 45) {
            $stage7StopReason = 'timeout_45_seconds'
        }
        if ($null -ne $stage7StopReason) { break }
        Start-Sleep -Milliseconds 100
    }
} catch {
    $stage7MonitorError = $_.Exception.Message
    $stage7StopReason = 'monitor_exception'
} finally {
    try {
        # This is the Process handle returned by this exact Start-Process call.
        # Never enumerate/stop another Blender, user P0, Unity or any other app.
        if (-not $stage7Process.HasExited) {
            if (-not $stage7StopReason) { $stage7StopReason = 'unexpected_monitor_exit' }
            $stage7Process.Kill()
        }
        $stage7ExitConfirmed = $stage7Process.WaitForExit(5000)
    } catch {
        $stage7CleanupError = $_.Exception.Message
    }
    $stage7Clock.Stop()
}
$stage7ExitCode = if ($stage7ExitConfirmed) { $stage7Process.ExitCode } else { $null }
$stage7AfterHash = (Get-FileHash -LiteralPath $stage7Source -Algorithm SHA256).Hash.ToLowerInvariant()
$stage7AfterInfo = Get-Item -LiteralPath $stage7Source
$stage7Run = [ordered]@{
    owned_blender_pid = $stage7OwnedPid
    process_exit_code = $stage7ExitCode
    process_exit_confirmed = $stage7ExitConfirmed
    monitor_error = $stage7MonitorError
    cleanup_error = $stage7CleanupError
    process_wall_seconds = [math]::Round($stage7Clock.Elapsed.TotalSeconds, 3)
    maximum_seconds = 45
    working_set_limit_bytes = $stage7LimitBytes
    peak_sampled_working_set_mib = [math]::Round($stage7PeakSampled / 1MB, 2)
    peak_OS_working_set_mib = [math]::Round($stage7PeakReported / 1MB, 2)
    stopped_for_limit = $stage7StopReason
    source_sha256_before = $stage7BeforeHash
    source_sha256_after = $stage7AfterHash
    source_unchanged = ($stage7AfterHash -eq $stage7ExpectedHash)
    source_read_only = $stage7AfterInfo.IsReadOnly
    source_bytes = $stage7AfterInfo.Length
    other_processes_stopped = $false
}
$stage7Run | ConvertTo-Json | Set-Content -LiteralPath $stage7Record -Encoding utf8
$stage7Run | ConvertTo-Json
Get-Content -LiteralPath $stage7Stdout -Tail 4
Get-Content -LiteralPath $stage7Stderr -Tail 4
if ($stage7StopReason -or $stage7MonitorError -or $stage7CleanupError -or -not $stage7ExitConfirmed -or $stage7ExitCode -ne 0 -or -not $stage7Run.source_unchanged) { exit 1 }
