param([ValidateSet('stage7package', 'stage7packager1', 'stage7packageinspect', 'stage7packager2')][string]$RunRecord = 'stage7package', [switch]$InspectOnly)
$ErrorActionPreference = 'Stop'
$stage7packageRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$stage7packageQa = Join-Path $stage7packageRoot 'qa/characters/plato/v002/einar-intake'
$stage7packageStdout = Join-Path $stage7packageQa ($RunRecord + '.stdout.log')
$stage7packageStderr = Join-Path $stage7packageQa ($RunRecord + '.stderr.log')
$stage7packageRecord = Join-Path $stage7packageQa ($RunRecord + '-run.json')
$stage7packageSource = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/project-management/source-cache/einar-v1/extracted/einar_release_v1.blend'
$stage7packageExe = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/production/.tools/blender/blender-4.5.15-windows-x64/blender.exe'
$stage7packageExpectedHash = '1c6663da0a2e9d6822978467c244e9186edc76083bae2414e02f9e695e711f7b'
$stage7packageSourceInfo = Get-Item -LiteralPath $stage7packageSource
$stage7packageBeforeHash = (Get-FileHash -LiteralPath $stage7packageSource -Algorithm SHA256).Hash.ToLowerInvariant()
if ($stage7packageBeforeHash -ne $stage7packageExpectedHash -or $stage7packageSourceInfo.Length -ne 91323760 -or -not $stage7packageSourceInfo.IsReadOnly) {
    throw 'Approved read-only source preflight mismatch'
}
New-Item -ItemType Directory -Path $stage7packageQa -Force | Out-Null
if (Test-Path -LiteralPath $stage7packageRecord) { throw 'Preserve previous invocation record; do not retry implicitly' }
$stage7packageArgs = @('--background', '--factory-startup', '--disable-autoexec', '--threads', '4', '--python-exit-code', '1', '--python', (Join-Path $PSScriptRoot 'verify-einar-closeup-package.py'))
if ($InspectOnly) { $stage7packageArgs += @('--', '--inspect-only') }
$stage7packageClock = [Diagnostics.Stopwatch]::StartNew()
$stage7packageProcess = Start-Process -FilePath $stage7packageExe -ArgumentList $stage7packageArgs -WorkingDirectory $stage7packageRoot -WindowStyle Hidden -RedirectStandardOutput $stage7packageStdout -RedirectStandardError $stage7packageStderr -PassThru
$stage7packageOwnedPid = $stage7packageProcess.Id
$stage7packageLimitBytes = [int64](1.2 * 1GB)
$stage7packagePeakSampled = [int64]0
$stage7packagePeakReported = [int64]0
$stage7packageStopReason = $null
$stage7packageMonitorError = $null
$stage7packageCleanupError = $null
$stage7packageExitConfirmed = $false
try {
    while (-not $stage7packageProcess.HasExited) {
        $stage7packageProcess.Refresh()
        if ($stage7packageProcess.HasExited) { break }
        $stage7packagePeakSampled = [math]::Max($stage7packagePeakSampled, $stage7packageProcess.WorkingSet64)
        $stage7packagePeakReported = [math]::Max($stage7packagePeakReported, $stage7packageProcess.PeakWorkingSet64)
        if ($stage7packageProcess.WorkingSet64 -gt $stage7packageLimitBytes -or $stage7packageProcess.PeakWorkingSet64 -gt $stage7packageLimitBytes) {
            $stage7packageStopReason = 'working_set_limit_1_2_GiB'
        } elseif ($stage7packageClock.Elapsed.TotalSeconds -ge 45) {
            $stage7packageStopReason = 'timeout_45_seconds'
        }
        if ($null -ne $stage7packageStopReason) { break }
        Start-Sleep -Milliseconds 100
    }
} catch {
    $stage7packageMonitorError = $_.Exception.Message
    $stage7packageStopReason = 'monitor_exception'
} finally {
    try {
        # This is the Process handle returned by this exact Start-Process call.
        # Never enumerate/stop another Blender, user P0, Unity or any other app.
        if (-not $stage7packageProcess.HasExited) {
            if (-not $stage7packageStopReason) { $stage7packageStopReason = 'unexpected_monitor_exit' }
            $stage7packageProcess.Kill()
        }
        $stage7packageExitConfirmed = $stage7packageProcess.WaitForExit(5000)
    } catch {
        $stage7packageCleanupError = $_.Exception.Message
    }
    $stage7packageClock.Stop()
}
$stage7packageExitCode = if ($stage7packageExitConfirmed) { $stage7packageProcess.ExitCode } else { $null }
$stage7packageAfterHash = (Get-FileHash -LiteralPath $stage7packageSource -Algorithm SHA256).Hash.ToLowerInvariant()
$stage7packageAfterInfo = Get-Item -LiteralPath $stage7packageSource
$stage7packageRun = [ordered]@{
    owned_blender_pid = $stage7packageOwnedPid
    process_exit_code = $stage7packageExitCode
    process_exit_confirmed = $stage7packageExitConfirmed
    monitor_error = $stage7packageMonitorError
    cleanup_error = $stage7packageCleanupError
    process_wall_seconds = [math]::Round($stage7packageClock.Elapsed.TotalSeconds, 3)
    maximum_seconds = 45
    working_set_limit_bytes = $stage7packageLimitBytes
    peak_sampled_working_set_mib = [math]::Round($stage7packagePeakSampled / 1MB, 2)
    peak_OS_working_set_mib = [math]::Round($stage7packagePeakReported / 1MB, 2)
    stopped_for_limit = $stage7packageStopReason
    source_sha256_before = $stage7packageBeforeHash
    source_sha256_after = $stage7packageAfterHash
    source_unchanged = ($stage7packageAfterHash -eq $stage7packageExpectedHash)
    source_read_only = $stage7packageAfterInfo.IsReadOnly
    source_bytes = $stage7packageAfterInfo.Length
    other_processes_stopped = $false
}
$stage7packageRun | ConvertTo-Json | Set-Content -LiteralPath $stage7packageRecord -Encoding utf8
$stage7packageRun | ConvertTo-Json
Get-Content -LiteralPath $stage7packageStdout -Tail 4
Get-Content -LiteralPath $stage7packageStderr -Tail 4
if ($stage7packageStopReason -or $stage7packageMonitorError -or $stage7packageCleanupError -or -not $stage7packageExitConfirmed -or $stage7packageExitCode -ne 0 -or -not $stage7packageRun.source_unchanged) { exit 1 }
exit 0
