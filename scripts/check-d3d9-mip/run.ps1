$ErrorActionPreference = 'Stop'
$root = $env:WINDOWS_LIBRETRO_TEST_ROOT
$results = $env:WINDOWS_LIBRETRO_RESULTS
$cc = @("$env:USERPROFILE/Codex/msys2-m27/msys64/mingw64/bin/gcc.exe",
        "$env:USERPROFILE/Codex/msys2-m27/msys64/ucrt64/bin/gcc.exe",'C:\msys64\mingw64\bin\gcc.exe','C:\msys64\ucrt64\bin\gcc.exe') |
    Where-Object { Test-Path $_ } | Select-Object -First 1
if (!$cc) { throw 'The MinGW compiler is unavailable' }
$env:PATH = (Split-Path $cc) + ';' + $env:PATH
$exe = Join-Path $root 'mip.exe'
& $cc -std=c11 -O2 -Wall -Wextra (Join-Path $root 'mip.c') -ld3d9 -lgdi32 -o $exe
if ($LASTEXITCODE) { throw "Compiler exit $LASTEXITCODE" }
& $exe | Tee-Object (Join-Path $results 'd3d9-mip.txt')
exit $LASTEXITCODE
