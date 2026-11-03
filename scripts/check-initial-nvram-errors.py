#!/usr/bin/env python3
"""Exercise actual core load failures with isolated broken-template fixtures.

No production source/template/save mutation. Fixtures replace one test dylib's
initial_nvram.o only. Content is loaded, not advanced, and no GL is requested.
"""
import argparse
import ctypes as C
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shlex
import subprocess

ROOT=Path(__file__).resolve().parent.parent
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--rom',type=Path,required=True,help='Existing vf2.zip, read only')
    p.add_argument('--system',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    assert args.rom.stem=='vf2','Fixtures target the existing VF2 template only'
    build=ROOT/'port/build-libretro-macos';core=build/'model2emuex_libretro.dylib'
    imported=ROOT/'src/libretro/sm2'
    commands=subprocess.check_output(['make','-n','-B'],cwd=ROOT,text=True)
    link=shlex.split(next(line for line in commands.splitlines() if ' -dynamiclib -o ' in line))
    source=(imported/'initial_nvram.cpp').read_text();table=(imported/'initial_nvram_templates.inc').read_text()
    spec=importlib.util.spec_from_file_location('network_frontend',ROOT/'scripts/test-network-conventions.py')
    abi=importlib.util.module_from_spec(spec);spec.loader.exec_module(abi)
    reports=[]
    def load(binary,name,enabled,error=None):
        f=abi.Frontend(binary,args.system,out/name)
        f.values[b'model2emuex_initial_nvram_setup']=b'enabled' if enabled else b'disabled'
        game=abi.Game(str(args.rom.resolve()).encode(),None,0,None)
        try:
            result=f.lib.retro_load_game(C.byref(game))
            if error:
                assert not result,(name,'Broken initialization was accepted')
                assert error in f.messages,(name,f.messages)
                assert f.message_levels[-1]==3,(name,'Expected RETRO_LOG_ERROR',f.message_levels)
                assert f.lib.retro_get_memory_size(0)==0,(name,'Failed content retained Save RAM')
            else:
                assert result,(name,'Normal/disabled initialization was rejected')
                assert f.lib.retro_get_memory_size(0)==65664
            reports.append({'case':name,'loaded':bool(result),'message':error,'passed':True})
        finally:f.close()
    load(core,'normal-enabled',True)
    for kind,error in [('invalid-template','Invalid embedded initial NVRAM template'),
                       ('invalid-layout','Embedded initial NVRAM template has an unsupported layout')]:
        work=out/kind;work.mkdir()
        fixture_source=source;fixture_table=table
        if kind=='invalid-template':
            fixture_table,count=re.subn(r'(\{"vf2",[^\n]+, )(0x[0-9a-f]+)(\},)',
                lambda m:m[1]+hex(int(m[2],16)^1)+m[3],table)
            assert count==1,'Exactly one template CRC must be corrupted'
        else:
            needle='if (!decode(*source, payload)) return SeedResult::InvalidTemplate;'
            assert source.count(needle)==1
            fixture_source=source.replace(needle,needle+'\n    if (game == "vf2") payload[0x3302] ^= 1; // test-only native-layout mismatch')
        cpp=work/'initial_nvram.cpp';cpp.write_text(fixture_source)
        (work/'initial_nvram_templates.inc').write_text(fixture_table)
        obj=work/'initial_nvram.o'
        subprocess.run(['clang++','-std=c++20','-O2','-fPIC','-fvisibility=hidden',
                        '-I'+str(imported),'-I'+str(imported/'include'),'-c',str(cpp),'-o',str(obj)],check=True)
        binary=work/'fixture.dylib';command=list(link)
        command[command.index('-o')+1]=str(binary)
        matches=[i for i,arg in enumerate(command) if arg.endswith('/sm2/initial_nvram.o')]
        assert len(matches)==1
        command[matches[0]]=str(obj)
        subprocess.run(command,cwd=ROOT,check=True)
        load(binary,kind+'-enabled',True,error)
        # Disabled is an ordinary no-op even when a faulty template exists.
        load(binary,kind+'-disabled',False)
    report={'core_sha256':hashlib.sha256(core.read_bytes()).hexdigest(),
            'native_frames_executed':0,'production_templates_modified':False,'cases':reports}
    (out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
