$ErrorActionPreference = 'Stop'
$payload = Join-Path $env:WINDOWS_LIBRETRO_TEST_ROOT 'payload'
$results = $env:WINDOWS_LIBRETRO_RESULTS
$exe = Join-Path $payload 'EMULATOR.EXE'
$expected = '2abe14866db96f4853b58bfaebc95d803c931a0e5ae33e95758c6b39520bccbc'
if ((Get-FileHash $exe -Algorithm SHA256).Hash.ToLower() -ne $expected) { throw 'Unrecognized original' }
Add-Type -Path (Join-Path $payload 'windows_exception_probe.cs')
$all = @()
foreach ($dividend in @([uint32]2147483647,[uint32]2147483648)) {
    $rows = [A68kWindowsExceptionProbe]::Run($exe,$payload,$dividend)
    $all += [pscustomobject]@{dividend=$dividend; rows=@($rows)}
    $all | ConvertTo-Json -Depth 8 | Set-Content (Join-Path $results 'windows-divs.json')
    if (@($rows | Where-Object { $_.kind -like 'probe-*' }).Count) { throw 'Original process did not reach or complete the probe; see windows-divs.json' }
}
$normal = @($all[0].rows | Where-Object kind -eq 'guest-overflow-tail')
$fault = @($all[1].rows | Where-Object { $_.kind -eq 'exception' -and $_.address -eq '0048198c' })
$exit = @($all[1].rows | Where-Object kind -eq 'process-exit')
if ($normal.Count -ne 1 -or $fault.Count -ne 2 -or $fault[0].firstChance -ne 1 -or $fault[1].firstChance -ne 0 -or $exit.Count -ne 1 -or $exit[0].code -ne $fault[1].code) {
    throw 'Original did not produce the expected control and unhandled DIVS fault'
}
@{original_sha256=$expected;os=[Environment]::OSVersion.VersionString;pointer_size=[IntPtr]::Size;
  evidence='Original process on Windows; synthetic DIVS operands after main-loop SEH registration; both exception chances declined by debugger; no ROMs.'
} | ConvertTo-Json | Set-Content (Join-Path $results 'provenance.json')
