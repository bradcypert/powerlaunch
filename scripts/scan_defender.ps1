# Scan an existing package without running its executable or changing exclusions.
[CmdletBinding()]
param(
    [string]$Root = 'build/defender-investigation',
    [switch]$PrepareOnly
)
$ErrorActionPreference = 'Stop'
$reportDirectory = Join-Path $Root 'reports'
New-Item -ItemType Directory -Force -Path $reportDirectory | Out-Null
$started = [DateTime]::UtcNow
$report = [ordered]@{
    started_utc = $started.ToString('o')
    verdict = 'scan_unavailable'
    exit_code = $null
    note = 'A scan result is not a guarantee of safety or the same cloud verdict on another device.'
}
function Write-Json($Value, [string]$Name) {
    $Value | ConvertTo-Json -Depth 12 | Set-Content -Encoding utf8 (Join-Path $reportDirectory $Name)
}
try {
    if ($env:OS -ne 'Windows_NT') { throw 'Microsoft Defender scanning requires Windows.' }
    $service = Get-Service -Name WinDefend -ErrorAction Stop
    if ($service.Status -ne 'Running') {
        # This enables the service on the disposable runner; it does not disable
        # any protection, restore a file, or add an exclusion.
        if ($service.StartType -eq 'Disabled') { Set-Service -Name WinDefend -StartupType Manual }
        Start-Service -Name WinDefend
    }
    $status = Get-MpComputerStatus -ErrorAction Stop
    Write-Json $status 'status-before.json'
    if (!$status.AMServiceEnabled -or !$status.AntivirusEnabled) {
        throw 'Defender antivirus is not enabled on this runner.'
    }
    Update-MpSignature -ErrorAction Stop
    $status = Get-MpComputerStatus -ErrorAction Stop
    Write-Json $status 'status-after-update.json'
    $preference = Get-MpPreference -ErrorAction Stop
    Write-Json ($preference | Select-Object MAPSReporting, SubmitSamplesConsent,
        DisableBlockAtFirstSeen, DisableRealtimeMonitoring) 'cloud-settings.json'
    if ($PrepareOnly) {
        $report.verdict = 'scanner_ready_not_scanned'
        return
    }
    $report.verdict = 'incomplete_scan'
    $inventory = Get-Content -Raw (Join-Path $reportDirectory 'inventory.json') | ConvertFrom-Json
    $package = (Resolve-Path (Join-Path $Root 'package')).Path
    function Assert-Inventory {
        foreach ($file in $inventory.files) {
            $path = Join-Path $package $file.path
            if (!(Test-Path -LiteralPath $path -PathType Leaf)) {
                throw "A package file is missing (possibly quarantined): $($file.path)"
            }
            if ((Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash.ToLowerInvariant() -ne $file.sha256) {
                throw "Package contents changed: $($file.path)"
            }
        }
    }
    Assert-Inventory
    $platform = Join-Path $env:ProgramData 'Microsoft/Windows Defender/Platform'
    $scanner = Get-ChildItem -Path (Join-Path $platform '*/MpCmdRun.exe') -ErrorAction SilentlyContinue |
        Sort-Object FullName -Descending | Select-Object -First 1 -ExpandProperty FullName
    if (!$scanner) { $scanner = Join-Path $env:ProgramFiles 'Windows Defender/MpCmdRun.exe' }
    if (!(Test-Path -LiteralPath $scanner -PathType Leaf)) { throw 'MpCmdRun.exe was not found.' }
    $report.scanner = $scanner
    $report.engine = $status.AMEngineVersion
    $report.signatures = $status.AntivirusSignatureVersion
    $report.scan_started_utc = [DateTime]::UtcNow.ToString('o')
    # Custom scan only: preserve evidence; no exclusions, allow rules or restores.
    # With remediation disabled, detections are in console output, not necessarily
    # Defender's UI/event log. Code 2 also covers scan errors, so do not call it
    # confirmed malware without reading the retained scanner output.
    $PSNativeCommandUseErrorActionPreference = $false
    & $scanner -Scan -ScanType 3 -File $package -DisableRemediation 2>&1 |
        Tee-Object -FilePath (Join-Path $reportDirectory 'scan-output.txt')
    $scanCode = $LASTEXITCODE
    $report.exit_code = $scanCode
    Assert-Inventory
    if ($scanCode -ne 0) {
        $report.verdict = 'detection_or_scan_error'
        throw "Defender returned $scanCode; review scan-output.txt before interpreting the result."
    }
    $report.verdict = 'no_detection_in_this_scan'
} catch {
    $report.error = $_.Exception.Message
    throw
} finally {
    $report.finished_utc = [DateTime]::UtcNow.ToString('o')
    try { Write-Json @(Get-MpThreatDetection -ErrorAction Stop) 'threat-detections.json' } catch {
        $_.Exception.Message | Set-Content (Join-Path $reportDirectory 'threat-query-error.txt')
    }
    Write-Json $report $(if ($PrepareOnly) { 'preparation.json' } else { 'scan-result.json' })
}
