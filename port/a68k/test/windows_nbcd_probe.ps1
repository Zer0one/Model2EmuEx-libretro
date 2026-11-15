$ErrorActionPreference = 'Stop'
$payload = Join-Path $env:WINDOWS_LIBRETRO_TEST_ROOT 'payload'
$results = $env:WINDOWS_LIBRETRO_RESULTS
$exe = Join-Path $payload 'EMULATOR.EXE'
$expected = '2abe14866db96f4853b58bfaebc95d803c931a0e5ae33e95758c6b39520bccbc'
if ((Get-FileHash $exe -Algorithm SHA256).Hash.ToLower() -ne $expected) { throw 'Unrecognized original' }
Add-Type -Path (Join-Path $payload 'windows_exception_probe.cs')
$rows = [A68kWindowsExceptionProbe]::RunNbcd($exe,$payload)
$rows | ConvertTo-Json -Depth 6 | Set-Content (Join-Path $results 'windows-nbcd.json')
if (@($rows | Where-Object kind -eq 'nbcd').Count -ne 512 -or @($rows | Where-Object kind -eq 'probe-incomplete').Count) { throw 'Incomplete NBCD acquisition' }
@{original_sha256=$expected;os=[Environment]::OSVersion.VersionString;pointer_size=[IntPtr]::Size;
  evidence='512 synthetic NBCD byte/X pairs in the original Windows process; native body and registered SEH; no ROMs.'} |
  ConvertTo-Json | Set-Content (Join-Path $results 'provenance.json')
