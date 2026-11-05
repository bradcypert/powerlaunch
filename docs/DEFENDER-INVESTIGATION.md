# Defender artifact investigation

On 2026-11-05 the maintainer reported `Trojan:Win32/Bearfoos.A!ml`, severity
Severe, status Quarantined, affecting `powerlaunch.exe` from Windows build run
[41964545729](https://github.com/bradcypert/powerlaunch/actions/runs/41964545729).
This is a reported detection, not a confirmed false positive or proof that
malware executed. Keep the file quarantined while investigating.

## Evidence identity

- Source commit: `7664373d436b50e49de3be5e4d629dca08c72cce`.
- Artifact: `powerlaunch-windows-x64`, ID `13387336305`.
- GitHub artifact ZIP SHA-256:
  `152c615540de92edcdcc00f3914cfc0811952d36c3b2caa4cd3acc03887a39b0`.
- Executable SHA-256 recorded in that build's memory profile:
  `d0aa642f1d6ad0af0eec15891dac892ecb26cdd4de78736b4beb739a1d9b8eb9`.

The existing build tests were functional/ownership checks, not antivirus scans.
Source inspection did not identify application installation/persistence behavior;
that does not clear compiled artifacts, the compiler, or bundled dependencies.

## Controlled scan

`Defender artifact investigation` scans the archived package on a disposable
Windows runner, without rebuilding or executing its EXE/DLLs. PR runs use the
reported artifact; manual dispatch may provide another artifact/run/hash tuple.
The artifact must remain available in GitHub's retention period.

1. Require a working Defender service and update security intelligence.
2. Authenticate to this repository's artifact API; verify run identity, the
   archive digest, and the expected executable hash before extraction.
3. Inventory all package files before extraction so the original hashes remain
   available even if real-time protection quarantines a member immediately.
4. Run an explicit custom scan with `-DisableRemediation`. This option preserves
   evidence for that scan, does not disable Defender, and ignores file exclusions.
   Real-time protection remains free to quarantine files. No allow rules, excluded
   paths, restored threats or modified application binaries are used.
5. Retain engine/signature versions, cloud settings, console output, detections,
   timestamps and the inventory. Missing/changed files, scan errors and unavailable
   Defender are failures, never clean scans. The diagnostic artifact contains
   reports only, not another copy of the executable.

A no-detection result on a hosted runner cannot reproduce every device's cloud
verdict or establish safety. If the detection reproduces, retain the exact bytes
and seek Microsoft's analysis before treating it as an incorrect detection.
No file has been manually submitted to Microsoft or a public multi-engine service
as part of this investigation.

## References

- [Microsoft's Bearfoos.A!ml description](https://www.microsoft.com/en-us/wdsi/threats/malware-encyclopedia-description?name=Trojan%3AWin32%2FBearfoos.A!ml&threatid=2147731250)
- [Defender command-line scan semantics](https://learn.microsoft.com/en-us/defender-endpoint/command-line-arguments-microsoft-defender-antivirus)
- [Protection history status meanings](https://support.microsoft.com/en-us/windows/security/windows-security/protection-history-in-the-windows-security-app)
- [Microsoft file-analysis submission portal](https://www.microsoft.com/en-us/wdsi/filesubmission)
