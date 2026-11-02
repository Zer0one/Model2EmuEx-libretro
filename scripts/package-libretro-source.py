#!/usr/bin/env python3
"""Create one matching-source archive shared by every platform job, as in SM2."""
import argparse
import gzip
import re
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
def git(*arguments):
    return subprocess.check_output(['git', '-C', str(root), *arguments])
if git('status', '--porcelain', '--untracked-files=normal').strip():
    parser.error('Matching source requires a clean committed checkout')
version = re.search(r'^display_version = "([0-9.]+)"$',
    (root/'src/libretro/model2emuex_dev_libretro.info').read_text(), re.M)[1]
args.output.mkdir(parents=True, exist_ok=False)
path = args.output/f'model2emuex-libretro-source-{version}.tar.gz'
path.write_bytes(gzip.compress(git('archive', '--format=tar',
    f'--prefix=Model2EmuEx-libretro-{version}/', 'HEAD'), mtime=0))
print(path)
