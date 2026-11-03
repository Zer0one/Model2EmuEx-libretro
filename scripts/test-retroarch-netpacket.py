#!/usr/bin/env python3
"""Bounded macOS Model2EmuEx network acceptance.
Config, startup and owned-process teardown adapted from SM2
scripts/test-retroarch-netpacket.py. No shared config/save mutation.
"""
import argparse,json,shutil,socket,subprocess,sys,time,re,struct,hashlib
from pathlib import Path
from retroarch_savestate_helpers import free_udp_port,post_escape_to_pid,take_screenshot,wait_while_alive

def quote_config(value):return str(value).replace('\\','\\\\').replace('"','\\"')

def write_config(root: Path, assets: Path, base_config: Path, port: int,
                 command_port: int, cabinets: int, window_x: int,
                 window_y: int, remote_port: int | None = None) -> list[str]:
    for directory in (
        "info", "saves", "states", "logs", "config", "remaps",
        "screenshots",
    ):
        (root / directory).mkdir(parents=True, exist_ok=True)

    values = {
        "config_save_on_exit": "false",
        "system_directory": assets,
        "savefile_directory": root / "saves",
        "savestate_directory": root / "states",
        "log_dir": root / "logs",
        "log_to_file": "false",
        "log_to_file_timestamp": "false",
        "log_verbosity": "true",
        "core_options_path": root / "config" / "core-options.cfg",
        "global_core_options": "true",
        "game_specific_options": "false",
        "input_remapping_directory": root / "remaps",
        "input_exit_emulator": "escape",
        "quit_press_twice": "false",
        "auto_overrides_enable": "false",
        "auto_remaps_enable": "false",
        "rgui_config_directory": root / "config",
        "content_history_enable": "false",
        "history_list_enable": "false",
        "content_history_path": root / "config" / "content_history.lpl",
        "content_favorites_path": root / "config" / "content_favorites.lpl",
        "sort_savefiles_enable": "false",
        "sort_savefiles_by_content_enable": "false",
        "savestate_auto_load": "false",
        "savestate_auto_save": "false",
        "pause_nonactive": "false",
        "video_driver": "gl",
        "video_fullscreen": "false",
        "video_windowed_fullscreen": "false",
        "video_window_custom_size_enable": "true",
        "video_windowed_position_width": "496",
        "video_windowed_position_height": "384",
        "video_windowed_position_x": str(window_x),
        "video_windowed_position_y": str(window_y),
        "video_scale": "1.000000",
        "video_window_save_positions": "false",
        "video_shader_enable": "false",
        "screenshot_directory": root / "screenshots",
        "notification_show_screenshot": "false",
        "menu_enable_widgets": "false",
        "video_font_enable": "false",
        "audio_driver": "null",
        "audio_enable": "false",
        "microphone_driver": "null",
        "microphone_enable": "false",
        "camera_allow": "false",
        "location_allow": "false",
        "ui_companion_enable": "false",
        "netplay_ip_port": str(port),
        "netplay_max_connections": str(cabinets),
        "netplay_public_announce": "false",
        "netplay_use_mitm_server": "false",
        "netplay_nat_traversal": "false",
        "netplay_check_frames": "0",
        "netplay_nickname": root.name,
        "input_autodetect_enable": "false",
        "libretro_info_path": root / "info",
        "network_cmd_enable": "true",
        "network_cmd_port": str(command_port),
    }
    if cabinets == 1:
        values["netplay_enable"] = "false"
    if remote_port is not None:
        values.update(network_remote_enable="true",
                      network_remote_enable_user_p1="true",
                      network_remote_base_port=str(remote_port))
    overrides = root / "netpacket-overrides.cfg"
    overrides.write_text(
        "".join(f'{key} = "{quote_config(value)}"\n' for key, value in values.items()),
        encoding="utf-8",
    )
    base_copy = root / "base-retroarch.cfg"
    shutil.copy2(base_config, base_copy)
    return ["-c", str(base_copy), f"--appendconfig={overrides}"]

def terminate_instance(process: subprocess.Popen[bytes]) -> bool:
    if process.poll() is not None:
        return False
    process.terminate()
    try:
        process.wait(timeout=5.0)
        return False
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5.0)
        return True


def log_contains(path: Path, text: str) -> bool:
    try:
        return text in path.read_text(encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return False


def close_instance(process: subprocess.Popen[bytes], command_port: int) -> bool:
    if process.poll() is not None:
        return False
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(b"QUIT\n", ("127.0.0.1", command_port))
        process.wait(timeout=8.0)
        return False
    except (OSError, subprocess.TimeoutExpired):
        if sys.platform != "darwin":
            return terminate_instance(process)
        try:
            post_escape_to_pid(process.pid)
            time.sleep(1.0)
            if process.poll() is None:
                post_escape_to_pid(process.pid)
            process.wait(timeout=5.0)
            return False
        except (OSError, RuntimeError, subprocess.TimeoutExpired):
            return terminate_instance(process)


def main():
 p=argparse.ArgumentParser(description=__doc__)
 for name in ('retroarch','core','rom','system','base-config','output'):p.add_argument('--'+name,type=Path,required=True)
 p.add_argument('--peer-rom',type=Path,action='append',default=[],help='Content for each client, in ring order')
 p.add_argument('--play',action='store_true');p.add_argument('--exercise',action='store_true')
 p.add_argument('--cabinets',type=int,default=2);p.add_argument('--settle',type=float,default=30)
 a=p.parse_args();assert 2<=a.cabinets<=8
 if a.peer_rom and len(a.peer_rom)!=a.cabinets-1:
  p.error('--peer-rom must identify every client when using mixed content')
 a.output=a.output.resolve();a.output.mkdir(parents=True,exist_ok=False)
 core=a.core.resolve();netport=free_udp_port()
 roms=[a.rom.resolve(strict=True)]+[r.resolve(strict=True) for r in a.peer_rom]
 if not a.peer_rom:roms*=a.cabinets
 processes=[];logs=[];results=[];ports=[];remotes=[]
 (a.output/'core-sha256.txt').write_text(hashlib.sha256(core.read_bytes()).hexdigest()+'\n')
 try:
  for index,rom in enumerate(roms):
   game=rom.stem
   role={'powsledm':'1','powsledr':'r','powsled':'2'}.get(game,str(index+1))
   root=a.output/('host' if index==0 else 'client'+str(index));root.mkdir();port=free_udp_port();ports.append(port);remote=free_udp_port();remotes.append(remote)
   config=write_config(root,a.system.resolve(),a.base_config.resolve(),netport,port,a.cabinets,40+index*520,80,remote)
   shutil.copy2(Path(__file__).resolve().parents[1]/'src/libretro/model2emuex_libretro.info',root/'info'/ (core.stem+'.info'))
   options={'model2emuex_linked_cabinets_'+game:str(a.cabinets),'model2emuex_automatic_network_'+game:role,
    'model2emuex_initial_nvram_setup':'enabled','model2emuex_nvram_settings':'disabled',
    'model2emuex_pipeline':'disabled','model2emuex_controller_profile_type':'test_service'}
   (root/'config/core-options.cfg').write_text(''.join(f'{k} = "{v}"\n' for k,v in options.items()))
   logpath=root/'run.log';log=logpath.open('wb');logs.append(log)
   command=[str(a.retroarch.resolve()),'-v',*config,'-L',str(core),*(['-H'] if index==0 else ['-C','127.0.0.1']),str(rom)]
   process=subprocess.Popen(command,cwd=root,stdout=log,stderr=subprocess.STDOUT);processes.append(process)
   results.append({'pid':process.pid,'root':str(root),'log':str(logpath),'command':command})
   (a.output/'pids.json').write_text(json.dumps(results,indent=2)+'\n')
   wait_while_alive(process,4)
  deadline=time.monotonic()+a.settle
  while time.monotonic()<deadline:
   for process in processes:wait_while_alive(process,min(.2,max(0,deadline-time.monotonic())))
  if a.play:
   with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
    def button(button):
     for pressed in (True,False):
      for remote in remotes:sock.sendto(struct.pack('@iiiiHxx',0,1,0,button,int(pressed)),('127.0.0.1',remote))
      time.sleep(.25)
    button(2);button(2);time.sleep(1);button(3)
    for stage in range(4):
     for process in processes:wait_while_alive(process,2)
     button(3)
    for process in processes:wait_while_alive(process,20)
  if a.exercise:
   # Commands go to owned sessions only. A native restart retains callbacks/peers.
   with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
    for port in ports:
     sock.sendto(b'RESET\n',('127.0.0.1',port));time.sleep(3)
   deadline=time.monotonic()+20
   while time.monotonic()<deadline:
    for process in processes:wait_while_alive(process,.1)
  for process,result,port in zip(processes,results,ports):
   result['screenshot']=str(take_screenshot(process,Path(result['root']),port,'linked'))
 finally:
  for process,result,port in zip(processes,results,ports):
   result['forced_kill']=close_instance(process,port);result['exit_code']=process.returncode
  for log in logs:log.close()
  for result in results:
   text=Path(result['log']).read_text(errors='replace')
   result['roster_ready']=f", {a.cabinets} cabinets" in text and 'Linked-cabinet roster ready' in text
   result['native_link_ready']='Native link: state=3' in text
   result['native_events']=re.findall(r'Native link:.*',text)
  (a.output/'result.json').write_text(json.dumps(results,indent=2)+'\n')
  print(json.dumps(results,indent=2))
 assert len(results)==a.cabinets and all(r['exit_code']==0 and not r['forced_kill'] and r['roster_ready'] and r['native_link_ready'] for r in results)
if __name__=='__main__':main()
