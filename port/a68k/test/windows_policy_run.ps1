param([string]$Compiler = 'C:/Users/User-0/Codex/msys2-m27/msys64/mingw64/bin/gcc.exe')
$ErrorActionPreference = 'Stop'
$root = $env:WINDOWS_LIBRETRO_TEST_ROOT
$results = $env:WINDOWS_LIBRETRO_RESULTS
$source = Join-Path $root 'source'
$exe = Join-Path $root 'a68k-policy.exe'
if (-not (Test-Path $Compiler -PathType Leaf)) { throw 'Existing compiler missing; do not install automatically.' }
$env:Path = (Split-Path $Compiler) + ';' + $env:Path
& $Compiler -std=c11 -Wall -Wextra -Werror -O2 (Join-Path $source 'divs_error_policy.c') (Join-Path $source 'test/divs_error_policy_windows.c') -o $exe *> (Join-Path $results 'compiler.log')
if ($LASTEXITCODE -ne 0) { throw "Policy compilation failed: $LASTEXITCODE" }
$rows = @()
foreach ($mode in @('stop_content', 'original')) {
    $process = Start-Process -FilePath $exe -ArgumentList $mode -WorkingDirectory $root -PassThru
    try {
        if (-not $process.WaitForExit(10000)) { throw 'Owned policy child timed out' }
        $exitCode = [BitConverter]::ToUInt32([BitConverter]::GetBytes([int]$process.ExitCode),0)
        $rows += [pscustomobject]@{mode=$mode;exit_code=('{0:x8}' -f $exitCode)}
    } finally {
        if (-not $process.HasExited) { $process.Kill(); $process.WaitForExit() }
        $process.Dispose()
    }
}
$rows | ConvertTo-Json | Set-Content (Join-Path $results 'policy.json')
if ($rows[0].exit_code -ne '00000000' -or $rows[1].exit_code -ne 'c0000095') { throw 'Unexpected policy exit codes' }
@{compiler=(Get-FileHash $Compiler -Algorithm SHA256);binary=(Get-FileHash $exe -Algorithm SHA256);
  os=[Environment]::OSVersion.VersionString;limits='Isolated policy child; no frontend or game execution.'} |
    ConvertTo-Json -Depth 5 | Set-Content (Join-Path $results 'provenance.json')
