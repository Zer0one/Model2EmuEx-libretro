param([string]$Dependency)
$ErrorActionPreference = 'Stop'
# Reuse the previously qualified original-renderer dependency; no installation.
if (-not $Dependency) { throw 'Pass -Dependency with an existing qualified x86 d3dx9_42.dll path.' }
Get-FileHash $dependency -Algorithm SHA256 | ConvertTo-Json | Set-Content (Join-Path $env:WINDOWS_LIBRETRO_RESULTS 'dependency.json')
Copy-Item $dependency (Join-Path $env:WINDOWS_LIBRETRO_TEST_ROOT 'payload/d3dx9_42.dll')
$exe = "$env:WINDIR\SysWOW64\WindowsPowerShell\v1.0\powershell.exe"
$script = Join-Path $env:WINDOWS_LIBRETRO_TEST_ROOT 'payload\windows_exception_probe.ps1'
& $exe -NoProfile -ExecutionPolicy Bypass -File $script
if ($LASTEXITCODE -ne 0) { throw "Windows original DIVS probe failed: $LASTEXITCODE" }
