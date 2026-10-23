param([ValidateSet('stage3', 'stage3r1')][string]$RunRecord = 'stage3')
$ErrorActionPreference = 'Stop'
$stage3Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$stage3Qa = Join-Path $stage3Root 'qa/characters/plato/v002/einar-intake'
$stage3Stdout = Join-Path $stage3Qa ($RunRecord + '.stdout.log')
$stage3Stderr = Join-Path $stage3Qa ($RunRecord + '.stderr.log')
$stage3Record = Join-Path $stage3Qa ($RunRecord + '-run.json')
$stage3Source = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/project-management/source-cache/einar-v1/extracted/einar_release_v1.blend'
$stage3Exe = 'D:/AI/PROJECT/hackathon_projects/Aholo_3D_AI_Hackathon/production/.tools/blender/blender-4.5.15-windows-x64/blender.exe'
$stage3ExpectedHash = '1c6663da0a2e9d6822978467c244e9186edc76083bae2414e02f9e695e711f7b'
$stage3SourceInfo = Get-Item -LiteralPath $stage3Source
$stage3BeforeHash = (Get-FileHash -LiteralPath $stage3Source -Algorithm SHA256).Hash.ToLowerInvariant()
if ($stage3BeforeHash -ne $stage3ExpectedHash -or $stage3SourceInfo.Length -ne 91323760 -or -not $stage3SourceInfo.IsReadOnly) {
    throw 'Approved read-only source preflight mismatch'
}
New-Item -ItemType Directory -Path $stage3Qa -Force | Out-Null
if (Test-Path -LiteralPath $stage3Record) { throw 'Preserve previous invocation record; do not retry implicitly' }
$stage3Args = @('--background', '--factory-startup', '--disable-autoexec', '--threads', '4', '--python-exit-code', '1', '--python', (Join-Path $PSScriptRoot 'inspect-einar-displacement.py'))
$stage3Clock = [Diagnostics.Stopwatch]::StartNew()
$stage3Process = Start-Process -FilePath $stage3Exe -ArgumentList $stage3Args -WorkingDirectory $stage3Root -WindowStyle Hidden -RedirectStandardOutput $stage3Stdout -RedirectStandardError $stage3Stderr -PassThru
$stage3OwnedPid = $stage3Process.Id
$stage3LimitBytes = [int64](1.2 * 1GB)
$stage3PeakSampled = [int64]0
$stage3PeakReported = [int64]0
$stage3StopReason = $null
$stage3MonitorError = $null
$stage3CleanupError = $null
$stage3ExitConfirmed = $false
try {
    while (-not $stage3Process.HasExited) {
        $stage3Process.Refresh()
        if ($stage3Process.HasExited) { break }
        $stage3PeakSampled = [math]::Max($stage3PeakSampled, $stage3Process.WorkingSet64)
        $stage3PeakReported = [math]::Max($stage3PeakReported, $stage3Process.PeakWorkingSet64)
        if ($stage3Process.WorkingSet64 -gt $stage3LimitBytes -or $stage3Process.PeakWorkingSet64 -gt $stage3LimitBytes) {
            $stage3StopReason = 'working_set_limit_1_2_GiB'
        } elseif ($stage3Clock.Elapsed.TotalSeconds -ge 45) {
            $stage3StopReason = 'timeout_45_seconds'
        }
        if ($null -ne $stage3StopReason) { break }
        Start-Sleep -Milliseconds 100
    }
} catch {
    $stage3MonitorError = $_.Exception.Message
    $stage3StopReason = 'monitor_exception'
} finally {
    try {
        # This is the Process handle returned by this exact Start-Process call.
        # Never enumerate/stop another Blender, user P0, Unity or any other app.
        if (-not $stage3Process.HasExited) {
            if (-not $stage3StopReason) { $stage3StopReason = 'unexpected_monitor_exit' }
            $stage3Process.Kill()
        }
        $stage3ExitConfirmed = $stage3Process.WaitForExit(5000)
    } catch {
        $stage3CleanupError = $_.Exception.Message
    }
    $stage3Clock.Stop()
}
$stage3ExitCode = if ($stage3ExitConfirmed) { $stage3Process.ExitCode } else { $null }
$stage3AfterHash = (Get-FileHash -LiteralPath $stage3Source -Algorithm SHA256).Hash.ToLowerInvariant()
$stage3AfterInfo = Get-Item -LiteralPath $stage3Source
$stage3Run = [ordered]@{
    owned_blender_pid = $stage3OwnedPid
    process_exit_code = $stage3ExitCode
    process_exit_confirmed = $stage3ExitConfirmed
    monitor_error = $stage3MonitorError
    cleanup_error = $stage3CleanupError
    process_wall_seconds = [math]::Round($stage3Clock.Elapsed.TotalSeconds, 3)
    maximum_seconds = 45
    working_set_limit_bytes = $stage3LimitBytes
    peak_sampled_working_set_mib = [math]::Round($stage3PeakSampled / 1MB, 2)
    peak_OS_working_set_mib = [math]::Round($stage3PeakReported / 1MB, 2)
    stopped_for_limit = $stage3StopReason
    source_sha256_before = $stage3BeforeHash
    source_sha256_after = $stage3AfterHash
    source_unchanged = ($stage3AfterHash -eq $stage3ExpectedHash)
    source_read_only = $stage3AfterInfo.IsReadOnly
    source_bytes = $stage3AfterInfo.Length
    other_processes_stopped = $false
}
$stage3Run | ConvertTo-Json | Set-Content -LiteralPath $stage3Record -Encoding utf8
$stage3Run | ConvertTo-Json
Get-Content -LiteralPath $stage3Stdout -Tail 4
Get-Content -LiteralPath $stage3Stderr -Tail 4
if ($stage3StopReason -or $stage3MonitorError -or $stage3CleanupError -or -not $stage3ExitConfirmed -or $stage3ExitCode -ne 0 -or -not $stage3Run.source_unchanged) { exit 1 }
