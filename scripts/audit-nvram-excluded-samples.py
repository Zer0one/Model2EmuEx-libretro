#!/usr/bin/env python3
"""Compare existing SM2 campaign value samples, including excluded settings.

No acquisition, emulator execution or source/save mutation. Pairwise variation
between an option's collected values avoids attributing a common boot delta to
every option. Reports shared changed bits, not proof of incorrect emulation.
"""
import argparse, collections, hashlib, importlib.util, itertools, json, re, subprocess, tomllib
import xml.etree.ElementTree as ET
from pathlib import Path

spec=importlib.util.spec_from_file_location('fields',Path(__file__).with_name('audit-nvram-shared-fields.py'))
fields=importlib.util.module_from_spec(spec);spec.loader.exec_module(fields)
def slug(x): return '-'.join(re.findall(r'[a-z0-9]+',str(x).lower()))
def norm(x): return slug(x).replace('-','')
# Explicit recipe suffix aliases: each is checked against current native labels.
ALIASES={
 'airwlkrs':{'game_difficulty':['difficulty'],'win_for_free_play':['win-freeplay']},
 'manxtt':{'laxey_number_of_lap':['laxey-laps','laxey-lap'],'tt_number_of_lap':['tt-laps','tt-lap']},
 'zerogun':{'extend_points':['extend-points'],'ranking_data':['ranking-data']},
 'vstriker':{'v_goal_time_set':['v-goal-time'],'pk_member_set':['pk-member']},
}
def docs(reference):
 files=sorted((reference/'data/diagnostic-menus').glob('*.yaml'))
 ruby='require "json";require "yaml";require "date";puts JSON.generate(ARGV.map{|p|[p,YAML.safe_load(File.read(p),permitted_classes:[Date],aliases:true)]})'
 return {d.get('game',{}).get('set',Path(p).stem):(Path(p),d) for p,d in json.loads(subprocess.check_output(['ruby','-e',ruby,*map(str,files)],text=True))}
def exclusions(game,layout):
 """Known native integrity bytes and update counter, from current source/YAML."""
 out=set()
 def mark(bank,off,size=2):out.update((bank,i) for i in range(off,off+size))
 if game in {'vf2','vf2a','vf2o','fvipers','schamp','sfight'}:mark('backup',0x3302)
 elif game in {'daytona','daytona93','daytonas','daytonagtx','desert'}:
  mark('backup',8);mark('backup',0x88);mark('eeprom',8)
 elif game in {'vcop2','vstriker'}:mark('backup',8);mark('backup',0x88)
 elif game=='von':
  for off in (8,0x44):mark('eeprom',off)
  for off in (0x14,0x220):mark('backup',off)
 elif game=='sgt24h':
  mark('eeprom',8);mark('eeprom',0x28);mark('backup',0x68,4)
 elif game in {'manxtt','manxttdx','rchase2','srallyc','srallycdx','srallycdxa'}:mark('eeprom',0)
 elif game in {'gunblade','stcc','stcca','stccb','stcco','topskatr'}:mark('eeprom',8)
 banks=layout.get('settings_banks',{})
 if 'eeprom' in str(layout.get('storage','')) and banks:
  for value in banks.values():
   if isinstance(value,dict) and isinstance(value.get('offset'),int):mark('eeprom',value['offset'],1 if game=='doa' else 2)
 counter=layout.get('update_counter',{})
 if isinstance(counter.get('offset'),int):mark('eeprom',counter['offset'],counter.get('size',1))
 return out

def write_review(result,output):
 groups=collections.defaultdict(lambda:dict(excluded=set(),other=set(),fields=set(),pairs=0))
 for pair in result['pairs']:
  if pair['common_prefix']:continue
  group=groups[pair['game']];group['pairs']+=1
  for label,excluded in zip(pair['labels'],pair['excluded']):group['excluded' if excluded else 'other'].add(label)
  for field in pair['shared']:group['fields'].add((field['memory'],field['offset']))
 counts=result['counts']
 lines=['# Excluded NVRAM Settings: Existing-Sample Comparison','',
        'Only existing files were read. No emulator execution, acquisition or settings change.', '',
        f"Read {counts['raw_files']} raw files. Identified {counts['excluded_options']} excluded menu rows; {counts['excluded_compared']} have at least two mapped value samples.", '',
        'A shared bit below means that it varies between collected values of each of the two settings. This is not proof that the option itself owns that bit: shared save metadata and runtime changes can also vary. Known checksum bytes and documented update counters are excluded. Different bits and different memory banks never count as sharing.', '',
        'The name filter is applied to each pair. Similar-name pairs are omitted from the requested review list. Remaining observations are grouped by game for readability; exact masks, counterpart settings, value pairs and file hashes are in report.json.', '',
        '## Shared Bits Outside The Name Filter','',
        '| Game | Excluded Options Involved | Other Options Involved | Shared Locations |',
        '| --- | --- | --- | --- |']
 for game,group in sorted(groups.items()):
  locs=', '.join(bank+' `'+offset+'`' for bank,offset in sorted(group['fields']))
  lines.append('| '+game+' | '+'; '.join(sorted(group['excluded']))+' | '+('; '.join(sorted(group['other'])) or 'Other excluded options in this row')+' | '+locs+' |')
 lines.extend(['','None of these shared locations matches a declared operator-value address in the current campaign mapping. They are retained for review rather than silently discarded or described as proven parameter conflicts. The prior empty list based only on declared mappings is superseded.','',
               '## Pairs Covered By The Name Filter','', '| Game | Options | Common Prefix |','| --- | --- | --- |'])
 for pair in result['pairs']:
  if pair['common_prefix']:lines.append('| '+pair['game']+' | '+' / '.join(pair['labels'])+' | '+pair['common_prefix']+' |')
 lines.extend(['','## Existing Samples Without Persistent Variation',''])
 for row in result['coverage']:
  if row['excluded'] and row['status']=='compared' and not row['changed_fields']:
   lines.append('- '+row['game']+' — '+row['label']+': collected values have identical persistent payloads; this does not prove absence of a transient write.')
 lines.extend(['','## No Comparable Value Series','', '| Game | Excluded Option | Available-Evidence Limit |','| --- | --- | --- |'])
 for row in result['coverage']:
  if row['excluded'] and row['status']!='compared':
   reason='No retained dedicated value series located; baselines or other-setting captures do not establish this option.'
   if row['game'] in {'powsled','powsledm','powsledr'} and row['key']=='country':reason='Only Export label documented; no distinct committed country values collected.'
   if row['game']=='motoraiddx' and row['key']=='engine_volume':reason='Informational OUT OF USE row, not selectable.'
   lines.append('| '+row['game']+' | '+row['label']+' | '+reason+' |')
 (output/'review.md').write_text('\n'.join(lines)+'\n')
 (output/'outside-name-filter.json').write_text(json.dumps([x for x in result['pairs'] if not x['common_prefix']],indent=2)+'\n')

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',type=Path,default=Path('../sm2-emu-libretro'));p.add_argument('--output',type=Path,required=True);a=p.parse_args();assert not a.output.exists()
 ref=a.reference.resolve();documents=docs(ref);rows,_=fields.campaign(ref);bygame=collections.defaultdict(list)
 catalog=collections.defaultdict(list)
 for c in fields.catalog(ref/'src/libretro/nvram_settings_data.inc'):catalog[c['game']].append(c)
 parents={g.attrib['name']:g.get('parent','') for g in ET.parse(ref/'data/games.xml').getroot().findall('game')}
 for row in rows:
  game=row['game'];route='zeroguna' if game=='zerogunaj' else game if game in catalog else parents.get(game,'')
  row['excluded']=not any(row['key']==c['key'] or norm(row['label'])==norm(c['label']) for c in catalog[route]);bygame[game].append(row)
 result={'historical_recipe_samples':[], 'scope':'Existing raw campaign samples; pairs with at least one excluded option; no new acquisition','coverage':[],'pairs':[],'files':[],'unmatched_samples':[]}
 cache={}
 def payload(root,name,bank):
  suffix='.nv' if bank=='backup' else '.eeprom';path=root/'saves'/(name+suffix)
  if not path.is_file():return None
  if path not in cache:
   data=path.read_bytes();assert len(data)==(16384 if bank=='backup' else 128),(path,len(data));cache[path]=data
   result['files'].append(dict(path=str(path),size=len(data),sha256=hashlib.sha256(data).hexdigest()))
  return cache[path]
 for game,options in sorted(bygame.items()):
  if not any(x['excluded'] for x in options):continue
  print('Comparing',game,flush=True)
  recipe=ref/'scripts'/('libretro_nvram_samples.'+game+'.toml')
  if not recipe.is_file():
   result['coverage'].extend(dict(game=game,key=x['key'],label=x['label'],excluded=x['excluded'],status='no dedicated recipe',samples=[]) for x in options);continue
  config=tomllib.loads(recipe.read_text());campaign=config.get('campaign',{});root=Path(campaign.get('output_dir','')).expanduser();root=root if root.is_absolute() else recipe.parent/root;root=root.resolve()
  summary=root/'summary.json'
  if not summary.is_file():
   result['coverage'].extend(dict(game=game,key=x['key'],label=x['label'],excluded=x['excluded'],status='dedicated campaign files unavailable',samples=[]) for x in options);continue
  entries=json.loads(summary.read_text());grouped=collections.defaultdict(list)
  recipe_suffixes={s.get('suffix') for s in config.get('samples',[])}
  for entry in entries:
   if entry.get('status')!='ok':continue
   name=entry['sample'];suffix=name.removeprefix(game+'-');suffix_slug=slug(suffix)
   if suffix not in recipe_suffixes:
    result['historical_recipe_samples'].append(dict(game=game,sample=name,reason='manifest sample absent from current recipe; mapped by current option prefix'))
   matches=[]
   for row in options:
    for prefix in {slug(row['key']),slug(row['label']),*ALIASES.get(game,{}).get(row['key'],[])}:
     if suffix_slug==prefix or suffix_slug.startswith(prefix+'-'):matches.append((len(prefix),row['key']))
   if not matches:
    if suffix not in {campaign.get('baseline_sample'),'base','operator-inventory'}:result['unmatched_samples'].append(dict(game=game,sample=name,reason='no option suffix mapping'))
    continue
   length=max(x[0] for x in matches);keys={key for n,key in matches if n==length};assert len(keys)==1,(game,name,keys)
   grouped[keys.pop()].append(name)
  # Restrict to documented persistent storage, so a runtime backup mirror is
  # not mislabelled as another setting. Mixed-storage boards retain both.
  layout=documents[game][1].get('nvram_layout',{});storage=str(layout.get('storage',''))
  banks=['backup','eeprom'] if 'eeprom' in storage and 'backup_ram' in storage else ['eeprom'] if 'eeprom' in storage else ['backup']
  if game in {'daytona','daytonagtx','desert'}:banks=['backup','eeprom']
  excluded_bytes=exclusions(game,layout);signatures={}
  for row in options:
   names=sorted(set(grouped[row['key']]));images={bank:[] for bank in banks};missing=[]
   for name in names:
    for bank in banks:
     value=payload(root,name,bank)
     if value is None:missing.append((name,bank))
     else:images[bank].append((name,value))
   masks={};witnesses={}
   for bank,values in images.items():
    if len(values)<2:continue
    _,base=values[0]
    for name,image in values[1:]:
     for off,(before,after) in enumerate(zip(base,image)):
      delta=before^after
      if delta and (bank,off) not in excluded_bytes:
       masks[(bank,off)]=masks.get((bank,off),0)|delta
       for bit in range(8):
        if delta & (1 << bit):witnesses.setdefault((bank,off,bit),dict(samples=[values[0][0],name],before=before,after=after))
   status='compared' if len(names)>=2 and not missing else 'fewer than two mapped samples' if len(names)<2 else 'missing payload'
   result['coverage'].append(dict(game=game,key=row['key'],label=row['label'],excluded=row['excluded'],status=status,samples=names,storage_banks=banks,changed_fields=[dict(memory=b,offset=hex(o),mask=hex(m)) for (b,o),m in sorted(masks.items())],missing_payloads=missing))
   if status=='compared':signatures[row['key']]=(masks,witnesses)
  for left,right in itertools.combinations(options,2):
   if not (left['excluded'] or right['excluded']) or left['key'] not in signatures or right['key'] not in signatures:continue
   lm,lw=signatures[left['key']];rm,rw=signatures[right['key']];shared=[]
   for bank,off in sorted(lm.keys()&rm.keys()):
    mask=lm[(bank,off)]&rm[(bank,off)]
    if mask:shared.append(dict(memory=bank,offset=hex(off),mask=hex(mask),left_witness={str(bit):lw[(bank,off,bit)] for bit in range(8) if mask&(1<<bit)},right_witness={str(bit):rw[(bank,off,bit)] for bit in range(8) if mask&(1<<bit)}))
   if shared:
    prefix=fields.related(left['label'],right['label'])
    result['pairs'].append(dict(game=game,keys=[left['key'],right['key']],labels=[left['label'],right['label']],excluded=[left['excluded'],right['excluded']],common_prefix=prefix,classification='approved name filter' if prefix else 'review',shared=shared))
 excluded=[x for x in result['coverage'] if x['excluded']];result['counts']=dict(excluded_options=len(excluded),excluded_compared=sum(x['status']=='compared' for x in excluded),raw_files=len(result['files']),pairs=len(result['pairs']),outside_name_filter=sum(not x['common_prefix'] for x in result['pairs']))
 # Every reported shared bit must have a real changed-value witness on both sides.
 for pair in result['pairs']:
  for shared in pair['shared']:
   for bit in range(8):
    if int(shared['mask'],0)&(1<<bit):
     for side in ('left_witness','right_witness'):
      w=shared[side][str(bit)];assert (w['before']^w['after'])&(1<<bit)
 a.output.mkdir(parents=True);(a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['counts']))
 write_review(result,a.output)

 for pair in result['pairs']:print(pair['game'],' / '.join(pair['labels']),pair['classification'],[(x['memory'],x['offset'],x['mask']) for x in pair['shared']])
 print('Unmapped suffixes:',len(result['unmatched_samples']))
if __name__=='__main__':main()
