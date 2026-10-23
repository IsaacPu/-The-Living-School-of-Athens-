param([ValidateSet('stage6eyekeys', 'stage6eyekeysr1')][string]$RunRecord = 'stage6eyekeys')
$ErrorActionPreference = 'Stop'
$stage6eyekeysRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$stage6eyekeysQa = Join-Path $stage6eyekeysRoot 'qa/characters/plato/v002/einar-intake'
$stage6eyekeysStdout = Join-Path $stage6eyekeysQa ($RunRecord + '.stdout.log')
$stage6eyekeysStderr = Join-Path $stage6eyekeysQa ($RunRecord + '.stderr.log')
$stage6eyekeysRecord = Join-Path $stage6eyekeysQa ($RunRecord + '-run.json')
$stage6eyekeysSource = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/project-management/source-cache/einar-v1/extracted/einar_release_v1.blend'
$stage6eyekeysExe = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/production/.tools/blender/blender-4.5.15-windows-x64/blender.exe'
$stage6eyekeysExpectedHash = '1c6663da0a2e9d6822978467c244e9186edc76083bae2414e02f9e695e711f7b'
$stage6eyekeysSourceInfo = Get-Item -LiteralPath $stage6eyekeysSource
$stage6eyekeysBeforeHash = (Get-FileHash -LiteralPath $stage6eyekeysSource -Algorithm SHA256).Hash.ToLowerInvariant()
if ($stage6eyekeysBeforeHash -ne $stage6eyekeysExpectedHash -or $stage6eyekeysSourceInfo.Length -ne 91323760 -or -not $stage6eyekeysSourceInfo.IsReadOnly) {
    throw 'Approved read-only source preflight mismatch'
}
New-Item -ItemType Directory -Path $stage6eyekeysQa -Force | Out-Null
if (Test-Path -LiteralPath $stage6eyekeysRecord) { throw 'Preserve previous invocation record; do not retry implicitly' }
$stage6eyekeysArgs = @('--background', '--factory-startup', '--disable-autoexec', '--threads', '4', '--python-exit-code', '1', '--python', (Join-Path $PSScriptRoot 'inspect-einar-eye-keys.py'))
$stage6eyekeysClock = [Diagnostics.Stopwatch]::StartNew()
$stage6eyekeysProcess = Start-Process -FilePath $stage6eyekeysExe -ArgumentList $stage6eyekeysArgs -WorkingDirectory $stage6eyekeysRoot -WindowStyle Hidden -RedirectStandardOutput $stage6eyekeysStdout -RedirectStandardError $stage6eyekeysStderr -PassThru
$stage6eyekeysOwnedPid = $stage6eyekeysProcess.Id
$stage6eyekeysLimitBytes = [int64](1.2 * 1GB)
$stage6eyekeysPeakSampled = [int64]0
$stage6eyekeysPeakReported = [int64]0
$stage6eyekeysStopReason = $null
$stage6eyekeysMonitorError = $null
$stage6eyekeysCleanupError = $null
$stage6eyekeysExitConfirmed = $false
try {
    while (-not $stage6eyekeysProcess.HasExited) {
        $stage6eyekeysProcess.Refresh()
        if ($stage6eyekeysProcess.HasExited) { break }
        $stage6eyekeysPeakSampled = [math]::Max($stage6eyekeysPeakSampled, $stage6eyekeysProcess.WorkingSet64)
        $stage6eyekeysPeakReported = [math]::Max($stage6eyekeysPeakReported, $stage6eyekeysProcess.PeakWorkingSet64)
        if ($stage6eyekeysProcess.WorkingSet64 -gt $stage6eyekeysLimitBytes -or $stage6eyekeysProcess.PeakWorkingSet64 -gt $stage6eyekeysLimitBytes) {
            $stage6eyekeysStopReason = 'working_set_limit_1_2_GiB'
        } elseif ($stage6eyekeysClock.Elapsed.TotalSeconds -ge 45) {
            $stage6eyekeysStopReason = 'timeout_45_seconds'
        }
        if ($null -ne $stage6eyekeysStopReason) { break }
        Start-Sleep -Milliseconds 100
    }
} catch {
    $stage6eyekeysMonitorError = $_.Exception.Message
    $stage6eyekeysStopReason = 'monitor_exception'
} finally {
    try {
        # This is the Process handle returned by this exact Start-Process call.
        # Never enumerate/stop another Blender, user P0, Unity or any other app.
        if (-not $stage6eyekeysProcess.HasExited) {
            if (-not $stage6eyekeysStopReason) { $stage6eyekeysStopReason = 'unexpected_monitor_exit' }
            $stage6eyekeysProcess.Kill()
        }
        $stage6eyekeysExitConfirmed = $stage6eyekeysProcess.WaitForExit(5000)
    } catch {
        $stage6eyekeysCleanupError = $_.Exception.Message
    }
    $stage6eyekeysClock.Stop()
}
$stage6eyekeysExitCode = if ($stage6eyekeysExitConfirmed) { $stage6eyekeysProcess.ExitCode } else { $null }
$stage6eyekeysAfterHash = (Get-FileHash -LiteralPath $stage6eyekeysSource -Algorithm SHA256).Hash.ToLowerInvariant()
$stage6eyekeysAfterInfo = Get-Item -LiteralPath $stage6eyekeysSource
$stage6eyekeysRun = [ordered]@{
    owned_blender_pid = $stage6eyekeysOwnedPid
    process_exit_code = $stage6eyekeysExitCode
    process_exit_confirmed = $stage6eyekeysExitConfirmed
    monitor_error = $stage6eyekeysMonitorError
    cleanup_error = $stage6eyekeysCleanupError
    process_wall_seconds = [math]::Round($stage6eyekeysClock.Elapsed.TotalSeconds, 3)
    maximum_seconds = 45
    working_set_limit_bytes = $stage6eyekeysLimitBytes
    peak_sampled_working_set_mib = [math]::Round($stage6eyekeysPeakSampled / 1MB, 2)
    peak_OS_working_set_mib = [math]::Round($stage6eyekeysPeakReported / 1MB, 2)
    stopped_for_limit = $stage6eyekeysStopReason
    source_sha256_before = $stage6eyekeysBeforeHash
    source_sha256_after = $stage6eyekeysAfterHash
    source_unchanged = ($stage6eyekeysAfterHash -eq $stage6eyekeysExpectedHash)
    source_read_only = $stage6eyekeysAfterInfo.IsReadOnly
    source_bytes = $stage6eyekeysAfterInfo.Length
    other_processes_stopped = $false
}
$stage6eyekeysRun | ConvertTo-Json | Set-Content -LiteralPath $stage6eyekeysRecord -Encoding utf8
$stage6eyekeysRun | ConvertTo-Json
Get-Content -LiteralPath $stage6eyekeysStdout -Tail 4
Get-Content -LiteralPath $stage6eyekeysStderr -Tail 4
if ($stage6eyekeysStopReason -or $stage6eyekeysMonitorError -or $stage6eyekeysCleanupError -or -not $stage6eyekeysExitConfirmed -or $stage6eyekeysExitCode -ne 0 -or -not $stage6eyekeysRun.source_unchanged) { exit 1 }
