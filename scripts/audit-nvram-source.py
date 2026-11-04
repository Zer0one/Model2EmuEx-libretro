#!/usr/bin/env python3
"""Compare current SM2 source, imported modules and actual NVRAM registration.

Reuse SM2's catalog parser and public template/routing APIs. Index existing
recipes, diagnostic YAML and sample summaries read-only. No workbook parsing,
sample acquisition, game execution or user-data mutation.
"""
import argparse
import ctypes as C
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import tomllib

ROOT=Path(__file__).resolve().parent.parent
FILES=('nvram_settings.h','nvram_settings.cpp','nvram_settings_data.inc',
       'initial_nvram.h','initial_nvram.cpp','initial_nvram_templates.inc',
       'save_ram.h','save_ram.cpp','automatic_network.h','automatic_network.cpp',
       'rom/game.cpp','rom/game_db.cpp','data/games.xml')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
def receipt(path):
    return {'path':str(path),'exists':path.is_file(),**({'sha256':sha(path)} if path.is_file() else {})}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',type=Path,default=ROOT.parent/'sm2-emu-libretro')
    p.add_argument('--output',type=Path,required=True,help='New isolated output directory')
    args=p.parse_args();ref=args.reference.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=False)
    build=ROOT/'port/build-libretro-macos';core=build/'model2emuex_libretro.dylib'
    imported=ROOT/'src/libretro/sm2';manifest=json.loads((imported/'IMPORT.json').read_text())
    report={'reference_head':subprocess.check_output(['git','-C',str(ref),'rev-parse','HEAD'],text=True).strip(),
            'reference_state':'Live working-copy file hashes, not HEAD alone',
            'core_sha256':sha(core),'source_files':[],'registration_errors':[],'games':[]}
    for file in FILES:
        dst=imported/file;source=ref/manifest['files'][file]['source']
        entry=manifest['files'][file]
        equal=source.read_bytes()==dst.read_bytes()
        adapted=entry.get('unchanged') is False and bool(entry.get('adaptation'))
        pinned_adaptation=adapted and sha(source)==entry.get('source_sha256')
        report['source_files'].append({'file':file,'reference_sha256':sha(source),'import_sha256':sha(dst),
            'equal':equal,'documented_adaptation':entry.get('adaptation') if adapted else None,
            'reference_matches':pinned_adaptation if adapted else equal,
            'manifest_matches':sha(dst)==entry['sha256']})
    wording=(imported/'menu_wording.h').read_text().split('namespace sm2::libretro {',1)[1].rsplit('\n}',1)[0].strip()
    report['menu_wording_functions_equal']=wording in (ref/'src/libretro/core_options.h').read_text()
    probe=out/'nvram-source-probe'
    subprocess.run(['clang++','-std=c++20','-O2','-I'+str(imported),'-I'+str(imported/'include'),
                    str(ROOT/'scripts/audit-nvram-source.cpp'),
                    *[str(build/'sm2'/f) for f in ('nvram_settings.o','initial_nvram.o','save_ram.o')],'-o',str(probe)],check=True)
    audit=module('sm2_nvram_catalog_audit',ref/'scripts/audit-nvram-core-catalog.py')
    # Use the current reference parser for each table; do not consult the workbook.
    audit.CORE_DATA=ref/'src/libretro/nvram_settings_data.inc';source_options=audit.parse_core_options()
    audit.CORE_DATA=imported/'nvram_settings_data.inc';destination_options=audit.parse_core_options()
    assert source_options==destination_options,'Imported catalog differs from current source'
    labels=list(dict.fromkeys(label for options in source_options.values() for option in options
               for label in [option['label'],*[label for key,label in option['values']]]))
    normalized=subprocess.check_output([str(probe),'--labels'],input='\n'.join(labels)+'\n',text=True).splitlines()
    assert len(labels)==len(normalized)
    format_label=dict(zip(labels,normalized))
    abi=module('model2_network_audit',ROOT/'scripts/test-network-conventions.py')
    frontend=abi.Frontend(core,out,out/'frontend')
    try:actual=dict(frontend.definitions)
    finally:frontend.close()
    expected=[]
    for catalog,options in source_options.items():
        for option in options:
            key='model2emuex_nvram_'+catalog+'_'+option['suffix'];expected.append(key)
            definition=actual.get(key)
            wanted=[(key,format_label[label]+(' (Default)' if key==option['default_key'] else '')) for key,label in option['values']]
            if not definition or definition['label']!=format_label[option['label']] or definition['default']!=option['default_key'] or definition['choices']!=wanted:
                report['registration_errors'].append(key)
    registered=[k for k in actual if k.startswith('model2emuex_nvram_') and k!='model2emuex_nvram_settings']
    report['registration_errors']+=sorted(set(registered)^set(expected))
    report['operator_fields']=len(expected);report['catalogs']=len(source_options)
    snapshot=json.loads((ROOT/'CORE_OPTIONS_IMPLEMENTED.json').read_text())
    snapshot={d['key']:d for d in snapshot}
    report['snapshot_errors']=[]
    for key in expected:
        a=actual[key];b=snapshot.get(key,{})
        if (a['label'],a['default'],a['choices'])!=(b.get('label'),b.get('default'),[(v['value'],v['label']) for v in b.get('values',[])]):
            report['snapshot_errors'].append(key)
    catalog=json.loads((ROOT/'src/libretro/data/mame_model2_catalog.json').read_text())['games']
    for game in catalog:
        name=game['name'];parent=game.get('parent') or ''
        metadata=name=='daytona93' or 'prototype' in game['title'].lower()
        fields=subprocess.check_output([str(probe),name,parent,'metadata' if metadata else 'check'],text=True).rstrip('\n').split('\t')
        mapped,template,count,check,policy=fields
        recipes=[]
        for source in dict.fromkeys([name,mapped,template]):
            if not source:continue
            recipe=ref/'scripts'/('libretro_nvram_samples.'+source+'.toml')
            item={'set':source,'yaml':receipt(ref/'data/diagnostic-menus'/(source+'.yaml')),'recipe':receipt(recipe)}
            if recipe.is_file():
                data=tomllib.loads(recipe.read_text());samples=data.get('samples',[])
                folder=data.get('campaign',{}).get('output_dir')
                if folder and '$' not in folder:
                    directory=Path(folder).expanduser()
                    if not directory.is_absolute():directory=(recipe.parent/directory).resolve()
                    item['campaign_manifest']=receipt(directory/'campaign.json')
                    summary=directory/'summary.json'
                    item['summary']=receipt(summary)
                    if summary.is_file():
                        rows=json.loads(summary.read_text())
                        if isinstance(rows,list):
                            item['summary_rows']=len(rows);item['summary_status_counts']={s:sum(r.get('status')==s for r in rows) for s in sorted({str(r.get('status')) for r in rows})}
                            # Old receipts may point to moved /tmp artifacts. Record the
                            # limit; do not invalidate accepted embedded templates.
                            paths=[Path(v).expanduser() for r in rows for k in ('saves','screenshots') for v in r.get(k,[])]
                            item['recorded_artifacts']=len(paths);item['recorded_paths_present']=sum(v.exists() for v in paths)
                            item['relocated_paths_present']=sum(not v.exists() and (directory/('screenshots' if v.suffix.lower()=='.png' else 'saves')/v.name).exists() for v in paths)
                item['recipe_samples']=len(samples)
            item['existing_reference_base']=receipt(Path.home()/'Documents/RetroArch/sm2-nvram-analysis'/source/'generated/saves'/(source+'-base.srm'))
            recipes.append(item)
        report['games'].append({'game':name,'parent':parent,'board':game['board'],'catalog':mapped,
            'fields':int(count),'template_source':template or None,'template_kind':'exact' if template==name else 'explicit_compatible_parent' if template else 'unavailable',
            'source_probe':check,'initial_policy':dict(v.split('=',1) for v in policy.split(';') if v),
            'prototype_scope':'Existing metadata only; no new qualification' if metadata else None,
            'reference_evidence':recipes,'destination_evidence':'See NVRAM_SOURCE_REVIEW.md; source-level checks are not frontend persistence proof'})
    report['passed']=all(x['reference_matches'] and x['manifest_matches'] for x in report['source_files']) and report['menu_wording_functions_equal'] and not report['registration_errors'] and not report['snapshot_errors']
    (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('operator_fields','catalogs','registration_errors','snapshot_errors','passed')},indent=2))
    for game in report['games']:print(game['game'],game['catalog'],game['fields'],game['template_kind'],game['source_probe'])
    assert report['passed'],'Source or registration mismatch; see report.json'

if __name__=='__main__':main()
