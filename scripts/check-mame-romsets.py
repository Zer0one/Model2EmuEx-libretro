#!/usr/bin/env python3
"""ROM-free checks of the compiled MAME catalogue and archive lookup contract."""
import argparse
import ctypes as c
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import struct
import zipfile
import zlib

ROOT = Path(__file__).resolve().parents[1]
class Entry(c.Structure):
    _fields_ = [('type', c.c_int), ('file', c.c_char_p)] + [(n, c.c_uint32) for n in ('arg','offset','size','crc','flags')]
class Game(c.Structure):
    _fields_ = [(n, c.c_char_p) for n in ('name','title','parent','shared','board')] + [
        ('width',c.c_int),('height',c.c_int),('fps',c.c_float),('hook',c.c_int),('hook_addr',c.c_uint32),
        ('roms',c.POINTER(Entry)),('inputs',c.c_void_p),('port_defaults',c.c_uint8*8),('input_fn',c.c_uint32)]
class Regions(c.Structure):
    _fields_ = [('ptr', c.POINTER(c.c_uint8)*32),('size',c.c_uint32*32),('option',c.c_uint32*32)]


def load(path):
    lib = c.CDLL(str(path))
    lib.m2_game_list.argtypes=[c.POINTER(c.c_int)];lib.m2_game_list.restype=c.POINTER(Game)
    lib.m2_find_game.argtypes=[c.c_char_p];lib.m2_find_game.restype=c.POINTER(Game)
    lib.m2_load_roms.argtypes=[c.POINTER(Game),c.POINTER(c.c_char_p),c.POINTER(Regions),c.c_void_p]
    lib.m2_load_roms_with_policy.argtypes=lib.m2_load_roms.argtypes+[c.c_uint]
    lib.m2_check_roms.argtypes=[c.POINTER(Game),c.POINTER(c.c_char_p),c.POINTER(c.c_int)]
    lib.m2_free_roms.argtypes=[c.POINTER(Regions)]
    return lib


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,required=True)
    args=parser.parse_args()
    # Compare generated outputs with the pinned MAME source, not a second copy of the manifest.
    subprocess.run(['python3',str(ROOT/'scripts/align-mame-romsets.py'),'--source',str(args.source),'--check'],check=True)
    spec=importlib.util.spec_from_file_location('align',ROOT/'scripts/align-mame-romsets.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    expected=module.parse_mame(args.source.read_text())
    manifest=json.loads((ROOT/'src/libretro/data/mame_model2_catalog.json').read_text())
    with tempfile.TemporaryDirectory(prefix='model2emuex-mame-check-') as temp:
        work=Path(temp)
        for mame,name in ((True,'aligned'),(False,'native')):
            command=['clang','-std=c11','-dynamiclib','-I'+str(ROOT/'port'),'-I'+str(ROOT/'src/libretro/data')]
            if mame:command+=['-DM2_ROMSET_MAME']
            subprocess.run(command+[str(ROOT/'port/m2/m2rom.c'),'-lz','-o',str(work/(name+'.dylib'))],check=True)
        lib=load(work/'aligned.dylib');native=load(work/'native.dylib')
        count=c.c_int(); games=lib.m2_game_list(c.byref(count));assert count.value==len(manifest['games'])==70
        assert sum(record['board'] == 'Model 2B' for record in manifest['games']) == 35
        assert sum(record['board'] == 'Model 2C' for record in manifest['games']) == 13
        native_count=c.c_int();native.m2_game_list(c.byref(native_count));assert native_count.value==29
        assert not lib.m2_find_game(b'srallyp') and native.m2_find_game(b'srallyp')
        assert not lib.m2_find_game(b'dayton93') and native.m2_find_game(b'dayton93')
        assert lib.m2_find_game(b'daytona93')
        for index,record in enumerate(manifest['games']):
            g=games[index];m=expected[g.name.decode()]
            assert g.name.decode()==record['name']
            assert g.title.decode()==m['title']
            assert (g.parent.decode() if g.parent else None)==m['parent']
            old=native.m2_find_game(record['native_name'].encode())
            if record.get('recovered_model2c'):
                assert not old and g.board == b'Model 2C'
            elif record['recovered_model2b'] or record['mame_revision_of'] or record.get('mame_cabinet'):
                assert not old and g.board == b'Model 2B'
            else:
                old=old.contents
                assert (g.hook,g.hook_addr,g.input_fn,g.board)==(old.hook,old.hook_addr,old.input_fn,old.board)
                assert bytes(g.port_defaults)==bytes(old.port_defaults)
            region=-1;program=[];entry=0
            while g.roms[entry].type>=0:
                e=g.roms[entry];entry+=1
                if e.type==0:region=e.arg&255
                if e.type!=1:continue
                assert e.crc and any(f['name']==e.file.decode() and f['size']==e.size and f['crc']==e.crc for f in m['files']), (g.name,e.file)
                if region==0:program.append((e.size,e.crc))
            assert sorted(program)==sorted((f['size'],f['crc']) for f in m['files'] if f['region']=='maincpu')
        # The approved Power Sled program patches are applied after ROM loading.
        patch_entries=(Entry*3)(Entry(0,None,0,8,0,0,0),
                                Entry(6,None,0x12345678,4,0,0,0),
                                Entry(-1,None,0,0,0,0,0))
        patch_game=Game(name=b'program_patch_fixture',roms=patch_entries)
        patch_dirs=(c.c_char_p*1)(None)
        patched=Regions()
        assert lib.m2_load_roms(c.byref(patch_game),patch_dirs,c.byref(patched),None)==0
        assert c.string_at(patched.ptr[0],8)==bytes.fromhex('0000000078563412')
        lib.m2_free_roms(c.byref(patched))
        # Native type-5 callback receives the whole region, not the stale
        # offset/length fields retained from the preceding file operation.
        transforms=(Entry*5)(Entry(0,None,6,9,0,0,0),
            Entry(2,None,0,9,0x12,0,0),Entry(2,None,1,1,0x34,0,0),
            Entry(5,None,0x4f77b0,0xffffffff,0xffffffff,0,0),
            Entry(-1,None,0,0,0,0,0))
        transform_game=Game(name=b'transform_fixture',roms=transforms)
        assert lib.m2_load_roms(c.byref(transform_game),patch_dirs,c.byref(patched),None)==0
        assert c.string_at(patched.ptr[6],9)==bytes.fromhex('341212121212121212')
        lib.m2_free_roms(c.byref(patched))
        transforms[3].arg=0xdeadbeef
        assert lib.m2_load_roms(c.byref(transform_game),patch_dirs,c.byref(patched),None)!=0
        lib.m2_free_roms(c.byref(patched))
        # Check a split-set fixture, using no copyrighted bytes. Shared files are
        # found in the canonical MAME parent archive even when their stored path differs.
        payload=b'ROM-free split-set fixture'
        crc=zlib.crc32(payload)
        entries=(Entry*3)(Entry(0,None,0,len(payload),0,0,0),Entry(1,b'canonical.bin',0,0,len(payload),crc,1),Entry(-1,None,0,0,0,0,0))
        fixture=Game(name=b'canonical_clone',parent=b'canonical_parent',roms=entries)
        dirs=(c.c_char_p*2)(str(work).encode(),None)
        for method in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED):
            with zipfile.ZipFile(work/'canonical_parent.zip','w',compression=method) as archive:
                archive.writestr('merged/path/renamed.bin',payload)
            total=c.c_int();assert lib.m2_check_roms(c.byref(fixture),dirs,c.byref(total))==0 and total.value==1
            result=Regions();assert lib.m2_load_roms(c.byref(fixture),dirs,c.byref(result),None)==0
            assert c.string_at(result.ptr[0],len(payload))==payload
            lib.m2_free_roms(c.byref(result))
        # Canonical MAME root sets have no parent. A missing selected ZIP must
        # still reach the optional shared archive without comparing against NULL.
        fixture.parent=None
        assert lib.m2_check_roms(c.byref(fixture),dirs,c.byref(total))==1
        fixture.shared=b'canonical_parent'
        assert lib.m2_check_roms(c.byref(fixture),dirs,c.byref(total))==0
        fixture.shared=b'model2'
        assert lib.m2_check_roms(c.byref(fixture),dirs,c.byref(total))==1
        # Payload verification must reject forged ZIP metadata, while Disabled
        # accepts explicitly requested non-matching bytes but never wrong sizes.
        fixture.shared=None
        fixture.parent=None
        def attempt(expected_status,policy):
            result=Regions()
            status=lib.m2_load_roms_with_policy(c.byref(fixture),dirs,c.byref(result),None,policy)
            assert (status==0)==expected_status,(policy,status)
            if expected_status:loaded=c.string_at(result.ptr[0],len(payload))
            lib.m2_free_roms(c.byref(result))
            return loaded if expected_status else None
        archive_path=work/'canonical_clone.zip'
        wrong=bytes([payload[0]^1])+payload[1:]
        for method in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED):
            with zipfile.ZipFile(archive_path,'w',compression=method) as archive:
                archive.writestr('canonical.bin',payload)
            assert attempt(True,3)==payload
            with zipfile.ZipFile(archive_path,'w',compression=method) as archive:
                archive.writestr('canonical.bin',wrong)
            assert attempt(True,0)==wrong
            attempt(False,3)
            forged=bytearray(archive_path.read_bytes())
            cd=forged.index(b'PK\x01\x02')
            struct.pack_into('<I',forged,cd+16,crc)
            struct.pack_into('<I',forged,14,crc)
            archive_path.write_bytes(forged)
            assert attempt(True,1)==wrong # Original metadata-only behavior.
            attempt(False,3)
            assert attempt(True,0)==wrong
            with zipfile.ZipFile(archive_path,'w',compression=method) as archive:
                archive.writestr('canonical.bin',payload+b'extra')
            attempt(False,0)
        archive_path.unlink()
        loose=work/'canonical_clone'/'canonical.bin';loose.parent.mkdir()
        loose.write_bytes(payload);assert attempt(True,3)==payload
        loose.write_bytes(wrong);attempt(False,3);assert attempt(True,0)==wrong
        loose.write_bytes(payload+b'extra');attempt(False,0)
        print('PASS: computed stored/deflated/loose payload CRCs; forged metadata rejection; Disabled bypass; strict size checks')
        print('PASS: compiled 70-set MAME metadata, all required filename/size/CRC tuples, program identity, native wiring, native ROM transforms, standalone isolation, split-parent and merged-path ZIP lookup')
if __name__=='__main__':main()
