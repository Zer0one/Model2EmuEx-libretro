#!/usr/bin/env python3
"""Targeted actual-core policy, legacy-state and unaffected VF2 comparison."""
import argparse,ctypes as C,hashlib,importlib.util,json,struct,sys,zipfile
from pathlib import Path
root=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('network_check',root/'scripts/test-network-conventions.py')
mod=importlib.util.module_from_spec(spec);sys.modules[spec.name]=mod;spec.loader.exec_module(mod)
p=argparse.ArgumentParser();p.add_argument('--previous-core',type=Path,required=True);p.add_argument('--rom-directory',type=Path,required=True);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
current=root/'port/build-libretro-macos/model2emuex_dev_libretro.dylib'
def frontend(core,name):
    f=mod.Frontend(core,out/'system',out/name)
    f.lib.retro_serialize.argtypes=[C.c_void_p,C.c_size_t];f.lib.retro_serialize.restype=C.c_bool
    f.lib.retro_unserialize.argtypes=[C.c_void_p,C.c_size_t];f.lib.retro_unserialize.restype=C.c_bool
    return f
def save(f):
    data=C.create_string_buffer(12*1024*1024);assert f.lib.retro_serialize(data,len(data));return data.raw
def load(f,data):return f.lib.retro_unserialize(C.create_string_buffer(data),len(data))
def header(data):return {'abi':hex(struct.unpack_from('<I',data,20)[0]),'bank':data[114],'auxiliary_present':data[115]}
old=frontend(args.previous_core,'old-manxtt');old.load(args.rom_directory/'manxtt.zip');old.run(30)
legacy=save(old);old.close();(out/'legacy.state').write_bytes(legacy)
f=frontend(current,'new-manxtt');f.load(args.rom_directory/'manxtt.zip')
option=f.definitions['model2emuex_manxtt_cabinet_audio'];assert option['default']=='enabled'
assert option['choices']==[('enabled','Enabled'),('disabled','Disabled')]
assert load(f,legacy);assert header(save(f))['bank']==0
f.run(2);assert header(save(f))['bank']==1
f.set({'model2emuex_nvram_settings':'enabled','model2emuex_nvram_manxtt_cabinet_type':'deluxe'});f.run(2)
deluxe=save(f);assert header(deluxe)['bank']==2 and header(deluxe)['auxiliary_present']==1
assert f.memory()[65536+10]==0
f.set({'model2emuex_manxtt_cabinet_audio':'disabled'});f.run();assert header(save(f))['bank']==0
assert any('Selected Set; additional Deluxe board connected' in m for m in f.messages)
f.set({'model2emuex_manxtt_cabinet_audio':'enabled'});f.run();assert header(save(f))['bank']==2
assert load(f,deluxe);f.close()
old=frontend(args.previous_core,'old-reject-new');old.load(args.rom_directory/'manxtt.zip');assert not load(old,deluxe);old.close()
paired=[]
for label,core in [('previous',args.previous_core),('current',current)]:
    f=frontend(core,'vf2-'+label);pcm=hashlib.sha256()
    f.batch=mod.abi.BATCH(lambda samples,n:(pcm.update(C.string_at(samples,n*4)) or n));f.lib.retro_set_audio_sample_batch(f.batch)
    f.load(args.rom_directory/'vf2.zip');f.run(898)
    ram=C.string_at(f.lib.retro_get_memory_data(2),f.lib.retro_get_memory_size(2))
    paired.append({'pcm':pcm.hexdigest(),'ram':hashlib.sha256(ram).hexdigest(),'sram':hashlib.sha256(f.memory()).hexdigest()});f.close()
assert paired[0]==paired[1],paired
# Exercise the real primary loader as well as the optional-region helper.
optional=out/'missing-auxiliary';optional.mkdir()
with zipfile.ZipFile(args.rom_directory/'manxtt.zip') as source,zipfile.ZipFile(optional/'manxtt.zip','w',zipfile.ZIP_DEFLATED) as target:
    for entry in source.infolist():
        if entry.CRC in (0x1b78da74,0x17e84e15):continue
        target.writestr(entry,source.read(entry))
shared=args.rom_directory/'model2.zip'
if shared.is_file():(optional/'model2.zip').symlink_to(shared.resolve())
f=frontend(current,'missing-auxiliary-run')
f.set({'model2emuex_nvram_settings':'enabled','model2emuex_nvram_manxtt_cabinet_type':'deluxe'})
f.load(optional/'manxtt.zip');assert header(save(f))['auxiliary_present']==0
assert any('Deluxe additional sound ROMs unavailable' in m for m in f.messages);f.close()
result={'legacy_read':True,'old_core_rejects_new_feature':True,'missing_auxiliary_content_loads':True,'menu_option':option,'twin_deluxe_selected_policy':True,'vf2_900_frames_equal':paired,'new_header':header(deluxe),'core_sha256':hashlib.sha256(current.read_bytes()).hexdigest()}
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
