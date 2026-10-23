param([ValidateSet('stage5', 'stage5r1')][string]$RunRecord = 'stage5')
$ErrorActionPreference = 'Stop'
$stage5Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$stage5Qa = Join-Path $stage5Root 'qa/characters/plato/v002/einar-intake'
$stage5Stdout = Join-Path $stage5Qa ($RunRecord + '.stdout.log')
$stage5Stderr = Join-Path $stage5Qa ($RunRecord + '.stderr.log')
$stage5Record = Join-Path $stage5Qa ($RunRecord + '-run.json')
$stage5Source = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/project-management/source-cache/einar-v1/extracted/einar_release_v1.blend'
$stage5Exe = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/production/.tools/blender/blender-4.5.15-windows-x64/blender.exe'
$stage5ExpectedHash = '1c6663da0a2e9d6822978467c244e9186edc76083bae2414e02f9e695e711f7b'
$stage5SourceInfo = Get-Item -LiteralPath $stage5Source
$stage5BeforeHash = (Get-FileHash -LiteralPath $stage5Source -Algorithm SHA256).Hash.ToLowerInvariant()
if ($stage5BeforeHash -ne $stage5ExpectedHash -or $stage5SourceInfo.Length -ne 91323760 -or -not $stage5SourceInfo.IsReadOnly) {
    throw 'Approved read-only source preflight mismatch'
}
New-Item -ItemType Directory -Path $stage5Qa -Force | Out-Null
if (Test-Path -LiteralPath $stage5Record) { throw 'Preserve previous invocation record; do not retry implicitly' }
$stage5Args = @('--background', '--factory-startup', '--disable-autoexec', '--threads', '4', '--python-exit-code', '1', '--python', (Join-Path $PSScriptRoot 'restore-einar-default-ab.py'))
$stage5Clock = [Diagnostics.Stopwatch]::StartNew()
$stage5Process = Start-Process -FilePath $stage5Exe -ArgumentList $stage5Args -WorkingDirectory $stage5Root -WindowStyle Hidden -RedirectStandardOutput $stage5Stdout -RedirectStandardError $stage5Stderr -PassThru
$stage5OwnedPid = $stage5Process.Id
$stage5LimitBytes = [int64](1.2 * 1GB)
$stage5PeakSampled = [int64]0
$stage5PeakReported = [int64]0
$stage5StopReason = $null
$stage5MonitorError = $null
$stage5CleanupError = $null
$stage5ExitConfirmed = $false
try {
    while (-not $stage5Process.HasExited) {
        $stage5Process.Refresh()
        if ($stage5Process.HasExited) { break }
        $stage5PeakSampled = [math]::Max($stage5PeakSampled, $stage5Process.WorkingSet64)
        $stage5PeakReported = [math]::Max($stage5PeakReported, $stage5Process.PeakWorkingSet64)
        if ($stage5Process.WorkingSet64 -gt $stage5LimitBytes -or $stage5Process.PeakWorkingSet64 -gt $stage5LimitBytes) {
            $stage5StopReason = 'working_set_limit_1_2_GiB'
        } elseif ($stage5Clock.Elapsed.TotalSeconds -ge 45) {
            $stage5StopReason = 'timeout_45_seconds'
        }
        if ($null -ne $stage5StopReason) { break }
        Start-Sleep -Milliseconds 100
    }
} catch {
    $stage5MonitorError = $_.Exception.Message
    $stage5StopReason = 'monitor_exception'
} finally {
    try {
        # This is the Process handle returned by this exact Start-Process call.
        # Never enumerate/stop another Blender, user P0, Unity or any other app.
        if (-not $stage5Process.HasExited) {
            if (-not $stage5StopReason) { $stage5StopReason = 'unexpected_monitor_exit' }
            $stage5Process.Kill()
        }
        $stage5ExitConfirmed = $stage5Process.WaitForExit(5000)
    } catch {
        $stage5CleanupError = $_.Exception.Message
    }
    $stage5Clock.Stop()
}
$stage5ExitCode = if ($stage5ExitConfirmed) { $stage5Process.ExitCode } else { $null }
$stage5AfterHash = (Get-FileHash -LiteralPath $stage5Source -Algorithm SHA256).Hash.ToLowerInvariant()
$stage5AfterInfo = Get-Item -LiteralPath $stage5Source
$stage5Run = [ordered]@{
    owned_blender_pid = $stage5OwnedPid
    process_exit_code = $stage5ExitCode
    process_exit_confirmed = $stage5ExitConfirmed
    monitor_error = $stage5MonitorError
    cleanup_error = $stage5CleanupError
    process_wall_seconds = [math]::Round($stage5Clock.Elapsed.TotalSeconds, 3)
    maximum_seconds = 45
    working_set_limit_bytes = $stage5LimitBytes
    peak_sampled_working_set_mib = [math]::Round($stage5PeakSampled / 1MB, 2)
    peak_OS_working_set_mib = [math]::Round($stage5PeakReported / 1MB, 2)
    stopped_for_limit = $stage5StopReason
    source_sha256_before = $stage5BeforeHash
    source_sha256_after = $stage5AfterHash
    source_unchanged = ($stage5AfterHash -eq $stage5ExpectedHash)
    source_read_only = $stage5AfterInfo.IsReadOnly
    source_bytes = $stage5AfterInfo.Length
    other_processes_stopped = $false
}
$stage5Run | ConvertTo-Json | Set-Content -LiteralPath $stage5Record -Encoding utf8
$stage5Run | ConvertTo-Json
Get-Content -LiteralPath $stage5Stdout -Tail 4
Get-Content -LiteralPath $stage5Stderr -Tail 4
if ($stage5StopReason -or $stage5MonitorError -or $stage5CleanupError -or -not $stage5ExitConfirmed -or $stage5ExitCode -ne 0 -or -not $stage5Run.source_unchanged) { exit 1 }
