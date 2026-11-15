param([Parameter(Mandatory=$true)][string]$Dependency,[Parameter(Mandatory=$true)][string]$XAudio,[switch]$ObserveBoard)
$ErrorActionPreference = 'Stop'
$payload = Join-Path $env:WINDOWS_LIBRETRO_TEST_ROOT 'payload'
$exe = Join-Path $payload 'EMULATOR.EXE'
$hash = (Get-FileHash $exe -Algorithm SHA256).Hash.ToLowerInvariant()
if ($hash -ne '2abe14866db96f4853b58bfaebc95d803c931a0e5ae33e95758c6b39520bccbc') { throw 'Unrecognized ElSemi binary' }
if ((Get-FileHash $Dependency -Algorithm SHA256).Hash -ne 'F8B9CFAB7FFFBC8F98E41AA439D72921DC180634A1FEBCA2A9D41A0DF35D3472') { throw 'Unrecognized D3DX9 dependency' }
Copy-Item $Dependency (Join-Path $payload 'd3dx9_42.dll')
$expected = '3fa4da55bdcb3287ab71c4d859df2f214267af692cd9faa1d56fbcbb3df98f90'
$name = 'scsp-pitch.exe'
if ($ObserveBoard) {
    $name = 'exchange.exe'
    $expected = 'b4b0b5ecc39b04e617e63435b156ecfd3b6147a85ff9b17022cc801c6d7c09a3'
    if ([IO.Path]::GetFileNameWithoutExtension($env:WINDOWS_LIBRETRO_CONTENT) -eq 'hotdo') {
        $name = 'exchange-hotdo.exe'
        $expected = '17d76984b255fa7d701d18f616e14f0df0082cb6ebe1371f1996544355d5891a'
    }
}
$diagnostic = Join-Path $payload $name
$diagnosticHash = (Get-FileHash $diagnostic -Algorithm SHA256).Hash.ToLowerInvariant()
if ($diagnosticHash -ne $expected) { throw 'Unexpected manifest-patched binary' }
if ((Get-FileHash $XAudio -Algorithm SHA256).Hash -ne '61b57170f7c6365714396072d22cb98746718c0f44c9f0d5c62fdb1b218639c7') { throw 'Unexpected XAudio2 DLL' }
Copy-Item $XAudio (Join-Path $payload 'XAudio2_6.dll')
$runtime = Split-Path -LiteralPath $XAudio
$dependencies = @{
    'D3DCompiler_42.dll' = '6C976311406C23AA71018D274DA0ECDEF43B6E3A3B0B01E941A5E8E4E974386C'
    'XAPOFX1_4.dll' = '0AEE44B12913A95840EE6431D90518B0D72C54A27392E21EE6995E2151554A06'
}
foreach ($name in $dependencies.Keys) {
    $path = Join-Path $runtime $name
    if ((Get-FileHash $path -Algorithm SHA256).Hash -ne $dependencies[$name]) { throw "Unexpected $name" }
    Copy-Item $path (Join-Path $payload $name)
}
$content = $env:WINDOWS_LIBRETRO_CONTENT
if (!(Test-Path -LiteralPath $content -PathType Leaf)) { throw "ROM not readable: $content" }
$romDir = Split-Path -LiteralPath $content
(Get-Content "$payload\base.ini") -replace '^;Dir1=.*', ('Dir1=' + $romDir) | Set-Content "$payload\EMULATOR.INI" -Encoding ascii
Add-Type @'
using System;
using System.Runtime.InteropServices;
public static class ScspPitchMemory {
    [DllImport("kernel32.dll",SetLastError=true)]
    public static extern bool ReadProcessMemory(IntPtr process, IntPtr addr, byte[] data, UIntPtr size, out UIntPtr read);
}
'@
$game = [IO.Path]::GetFileNameWithoutExtension($content)
if ($game -notmatch '^[a-zA-Z0-9_]+$') { throw 'Unexpected set name' }
$p = Start-Process $diagnostic -ArgumentList $game -WorkingDirectory $payload -PassThru
try {
    $clock = [Diagnostics.Stopwatch]::StartNew()
    $rows = @()
    $buffer = [byte[]]::new(4098)
    do {
        Start-Sleep -Milliseconds 40
        $p.Refresh()
        if ($p.HasExited) { throw "Original process exited before table acquisition: $($p.ExitCode)" }
        if ($ObserveBoard) {
            $values = foreach ($at in 0x528d40,0x10482ac,0x5aa76c,0x528d34,0x10bfd60,0x10ed99e,
                    0x10682d0,0x106e2d0,0x10702d0,0x109bd1c,0x109bd24,0x109c50c) {
                $word = [byte[]]::new(4)
                $bytesRead = [UIntPtr]::Zero
                if (![ScspPitchMemory]::ReadProcessMemory($p.Handle,[IntPtr]$at,$word,[UIntPtr]4,[ref]$bytesRead) -or $bytesRead.ToUInt64() -ne 4) {
                    throw "Cannot read address $at"
                }
                [BitConverter]::ToUInt32($word,0)
            }
            if ($values[4] -gt 0 -and $values[1] -eq 0x4aeac0 -and $values[3] -ne 0 -and
                    ($rows.Count -eq 0 -or $rows[-1].frame -ne ($values[2] -band 255))) {
                $rows += @{live=$values[0]; configured=$values[1]; frame=($values[2] -band 255);
                           pc=$values[3]; frames_per_block=$values[4]; mixer=($values[5] -band 255);
                           ram_fetch_base=$values[6]; program_fetch_base=$values[7]; sample_fetch_base=$values[8];
                           voice_ram=$values[9]; dsp_ram=$values[10]; dsp_code=$values[11]}
            }
            if ($rows.Count -ge 16) {
                $noise = [byte[]]::new(1024)
                $n = [UIntPtr]::Zero
                if (![ScspPitchMemory]::ReadProcessMemory($p.Handle,[IntPtr]0x10bdf50,$noise,[UIntPtr]1024,[ref]$n) -or $n.ToUInt64() -ne 1024) {
                    throw 'Cannot read the initialized amplitude noise table'
                }
                $hasher = [Security.Cryptography.SHA256]::Create()
                try { $digest = [BitConverter]::ToString($hasher.ComputeHash($noise)).Replace('-','').ToLowerInvariant() }
                finally { $hasher.Dispose() }
                @{game=$game; original_sha256=$hash; diagnostic_sha256=$diagnosticHash; samples=$rows; noise_table_sha256=$digest} |
                    ConvertTo-Json -Depth 4 | Set-Content (Join-Path $env:WINDOWS_LIBRETRO_RESULTS 'exchange.json') -Encoding ascii
                return
            }
            continue
        }
        $read = [UIntPtr]::Zero
        $ok = [ScspPitchMemory]::ReadProcessMemory($p.Handle,[IntPtr]0x10c0168,$buffer,[UIntPtr]4098,[ref]$read)
        if ($ok -and $read.ToUInt64() -eq 4098) {
            $control = [BitConverter]::ToUInt16($buffer,4096)
            if ($control -and [BitConverter]::ToUInt32($buffer,0) -eq 180633600) {
                $table = [uint32[]]::new(1024)
                [Buffer]::BlockCopy($buffer,0,$table,0,4096)
                @{original_sha256=$hash;diagnostic_sha256=$diagnosticHash;game=$game;
                  os=[Environment]::OSVersion.VersionString;control_word=$control;table=$table} |
                    ConvertTo-Json -Depth 3 | Set-Content "$env:WINDOWS_LIBRETRO_RESULTS\pitch.json" -Encoding ascii
                return
            }
        }
    } while ($clock.Elapsed.TotalSeconds -lt 60)
    throw 'Acquisition did not complete in 60 seconds'
} finally {
    if (!$p.HasExited) { $p.Kill(); $p.WaitForExit(3000) | Out-Null }
    $p.Dispose()
}
