#!/usr/bin/env python3
"""Package the native core, notices and matching committed source (SM2 convention)."""
import argparse
import ctypes
import gzip
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = 'https://github.com/Zer0one/Model2EmuEx-libretro'


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args])


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core', type=Path, required=True)
    parser.add_argument('--source-archive', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--platform', choices=['macos-arm64', 'macos-x86_64', 'linux-x86_64', 'linux-arm64', 'windows-x86_64'], required=True)
    args = parser.parse_args()
    if git('status', '--porcelain', '--untracked-files=normal').strip():
        parser.error('Commit approved changes before release packaging')
    core = args.core.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    info = (ROOT / 'src/libretro/model2emuex_libretro.info').read_text()
    version = re.search(r'^display_version = "([0-9.]+)"$', info, re.M)
    assert version, 'Missing release version'
    version = version[1]
    revision = git('rev-parse', 'HEAD').decode().strip()
    expected_arch = args.platform.rsplit('-', 1)[1]
    binary_format = subprocess.check_output(['file', str(core)], text=True)
    if args.platform.startswith('macos-'):
        architecture = subprocess.check_output(['lipo', '-archs', str(core)], text=True).strip()
        assert architecture == expected_arch, architecture
        dependencies = subprocess.check_output(['otool', '-L', str(core)], text=True)
        for line in dependencies.splitlines()[2:]:
            dependency = line.strip().split(' (')[0]
            assert dependency.startswith(('/usr/lib/', '/System/Library/')), dependency
        exports = subprocess.check_output(['nm', '-gUj', str(core)], text=True).splitlines()
        assert exports and all(name.startswith('_retro_') for name in exports), exports
    elif args.platform.startswith('linux-'):
        assert 'ELF 64-bit' in binary_format, binary_format
        assert ('aarch64' if expected_arch == 'arm64' else 'x86-64') in binary_format, binary_format
        dependencies = subprocess.check_output(['ldd', str(core)], text=True)
        assert 'not found' not in dependencies, dependencies
        assert '/home/' not in dependencies and '/usr/local/' not in dependencies, dependencies
        exports = subprocess.check_output(['nm', '-D', '--defined-only', str(core)], text=True).splitlines()
        assert exports and all(line.split()[-1].startswith('retro_') for line in exports), exports
    else:
        assert 'PE32+' in binary_format and 'x86-64' in binary_format, binary_format
        details = subprocess.check_output(['objdump', '-p', str(core)], text=True)
        dependencies = '\n'.join(line.strip() for line in details.splitlines() if 'DLL Name:' in line)
        assert not re.search(r'lib(?:gcc|stdc|winpthread|z)', dependencies, re.I), dependencies
        names = details.split('[Ordinal/Name Pointer] Table', 1)[1].split('\n\n', 1)[0]
        exports = [line.split()[-1] for line in names.splitlines()
                   if re.match(r'\s*\[\s*\d+\]', line)]
        assert exports and all(name.startswith('retro_') for name in exports), exports

    class SystemInfo(ctypes.Structure):
        _fields_ = [('name', ctypes.c_char_p), ('version', ctypes.c_char_p),
                    ('extensions', ctypes.c_char_p), ('fullpath', ctypes.c_bool),
                    ('block_extract', ctypes.c_bool)]

    library = ctypes.CDLL(str(core))
    library.retro_get_system_info.argtypes = [ctypes.POINTER(SystemInfo)]
    actual = SystemInfo()
    library.retro_get_system_info(ctypes.byref(actual))
    assert library.retro_api_version() == 1
    assert (actual.name, actual.version, actual.extensions) == (
        b'Model2EmuEx', version.encode(), b'zip')
    assert actual.fullpath and actual.block_extract
    subprocess.run(['python3', str(ROOT / 'scripts/check-abi.py'), str(core)], check=True)

    source_name = f'model2emuex-libretro-source-{version}.tar.gz'
    source = output / source_name
    shutil.copy2(args.source_archive, source)
    assert gzip.decompress(source.read_bytes()) == git('archive', '--format=tar',
        f'--prefix=Model2EmuEx-libretro-{version}/', 'HEAD'), 'Source does not match this commit'
    with tarfile.open(source) as archive:
        names = archive.getnames()
        assert any(name.endswith('/src/libretro/libretro.c') for name in names)
        assert not any('/build-libretro-' in name or '/audit/' in name for name in names)

    package = output / 'package'
    (package / 'licenses').mkdir(parents=True)
    for origin, target in [
        (core, 'model2emuex_libretro' + core.suffix),
        (ROOT / 'src/libretro/model2emuex_libretro.info', 'model2emuex_libretro.info'),
        (ROOT / 'NOTICE.md', 'NOTICE.md'),
        (ROOT / 'LIBRETRO.md', 'README.md'),
        (ROOT / 'src/libretro/sm2/LICENSE.sm2', 'licenses/GPL-3.0.txt'),
        (ROOT / 'src/libretro/sm2/NOTICE.sm2', 'licenses/NOTICE.sm2'),
        (ROOT / 'src/libretro/sm2/licenses/BSD-3-Clause.txt', 'licenses/BSD-3-Clause.txt'),
        (ROOT / 'port/ymfm/LICENSE', 'licenses/ymfm.txt'),
        (ROOT / 'port/imgui/LICENSE.txt', 'licenses/ImGui.txt'),
    ]:
        shutil.copy2(origin, package / target)
    if (ROOT / 'LICENSE').exists():
        shutil.copy2(ROOT / 'LICENSE', package / 'LICENSE')
    # Retain actual bundled permission notices; donor NOTICE lists more
    # dependencies than this core uses, so it is not a package inventory.
    texts = {
        'Musashi.txt': (ROOT / 'port/m68k/m68kcpu.c').read_text().split('/* ================================= NOTES')[0],
        'SoftFloat-2b.txt': (ROOT / 'port/m68k/softfloat/softfloat.c').read_text().split('#include')[0],
        'pugixml.txt': (ROOT / 'src/libretro/sm2/pugixml/pugixml.cpp').read_text().rsplit('/**', 1)[1],
        'stb_image.txt': (ROOT / 'src/libretro/sm2/include/stb_image.h').read_text().rsplit('/*', 1)[1],
        'libretro-api.txt': (ROOT / 'src/libretro/include/libretro.h').read_text().split('*/', 1)[0] + '*/\n',
    }
    for name, text in texts.items():
        assert 'Copyright' in text or 'John R. Hauser' in text, name
        (package / 'licenses' / name).write_text(text)
    provenance = {
        'repository': REPOSITORY, 'revision': revision, 'version': version,
        'worktree_dirty': False, 'platform': args.platform,
        'minimum_macos': '13.0' if args.platform.startswith('macos-') else None, 'core_sha256': sha(core),
        'upstream': {'repository': 'https://github.com/octavioCuatrochio/Model2EmuEx',
                     'branch': 'daytona_decomp',
                     'revision': '25d82be56f339c754cc566f771ca9ffb90b69289'},
        'source_archive': source_name, 'source_sha256': sha(source),
    }
    (package / 'SOURCE.json').write_text(json.dumps(provenance, indent=2) + '\n')
    (package / 'SOURCE_COMMIT.txt').write_text(revision + '\n')
    payloads = sorted(p for p in package.rglob('*') if p.is_file())
    (package / 'SHA256SUMS').write_text(''.join(
        f'{sha(p)}  {p.relative_to(package).as_posix()}\n' for p in payloads))
    archive_path = output / f'model2emuex-libretro-{args.platform}-{version}.zip'
    with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(package.rglob('*')):
            if path.is_file():
                archive.write(path, path.relative_to(package))
    with zipfile.ZipFile(archive_path) as archive:
        assert archive.testzip() is None
        for path in payloads:
            assert hashlib.sha256(archive.read(path.relative_to(package).as_posix())).hexdigest() == sha(path)
    (output / 'SHA256SUMS').write_text(''.join(
        f'{sha(p)}  {p.name}\n' for p in (archive_path, source)))
    print(json.dumps(provenance, indent=2))
    print('PASS: architecture, ABI/version, exports, dependencies, source and archive checksums')


if __name__ == '__main__':
    main()
