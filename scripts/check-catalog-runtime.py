#!/usr/bin/env python3
"""Bounded M33 startup/state witnesses; reads existing ROM archives in place.

The 20-set scope is explicit. A successful process is not a gameplay or visual
acceptance claim. Keep screenshots/logs and compact hashes; remove raw state,
PCM and RAM captures only after their result is indexed.
"""
import argparse, hashlib, json, os, subprocess, time
from pathlib import Path
SETS=('doaa','pltkidsa','dyndeka2','dynamcop','zerogunaj','zeroguna',
      'doaab','doaae','hotd','hotdp','manxttdx','motoraiddx','srallycc',
      'srallycdx','srallycdxa','stcco','topskatruo','airwlkrs','hpyagu98','rascot2')
STATES={'doaa','pltkidsa','dynamcop','zeroguna','manxttdx','hotdp','airwlkrs','hpyagu98','rascot2'}
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('harness','core','roms','output'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--sets',nargs='+',choices=SETS,default=SETS)
 p.add_argument('--frames',type=int,default=900);a=p.parse_args()
 assert 1<=a.frames<=7200
 a.output.mkdir(parents=True,exist_ok=False);rows=[]
 for name in a.sets:
  content=a.roms/(name+'.zip');out=a.output/name;out.mkdir()
  log=a.output/(name+'.log');env=os.environ.copy()
  for key in list(env):
   if key.startswith('CHECK_'):env.pop(key)
  if name in STATES:env['CHECK_STATE']='1'
  if name in ('hotdp','rascot2'):env['CHECK_TGPX4_STATE']='1'
  start=time.monotonic();error=None
  with log.open('wb') as stream:
   try:r=subprocess.run([str(a.harness.resolve()),str(a.core.resolve()),str(content),str(a.frames),str(out.resolve())],stdout=stream,stderr=subprocess.STDOUT,env=env,timeout=120)
   except subprocess.TimeoutExpired:r=None;error='120-second owned-process timeout'
  text=log.read_text(errors='replace');files=[]
  for f in sorted(out.iterdir()):
   if f.is_file():
    files.append(dict(name=f.name,size=f.stat().st_size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
  row=dict(set=name,frames=a.frames,state_requested=name in STATES,returncode=r.returncode if r else None,error=error,elapsed_seconds=round(time.monotonic()-start,3),harness_pass=('PASS:' in text or 'PASS Save States:' in text) and r is not None and r.returncode==0,files=files)
  rows.append(row);(a.output/'results.json').write_text(json.dumps(rows,indent=2)+'\n')
  # A failing witness retains raw state for diagnosis. Successful raw payloads
  # can be reproduced; preserve the native image and exact-file hash receipt.
  if row['harness_pass']:
   for f in out.iterdir():
    if f.is_file() and f.name!='core.ppm':f.unlink()
  print(name,'PASS' if row['harness_pass'] else 'FAIL',row['elapsed_seconds'],flush=True)
 print('Witnesses:',sum(r['harness_pass'] for r in rows),'/',len(rows),flush=True)
if __name__=='__main__':main()
