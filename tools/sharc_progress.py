#!/usr/bin/env python3
"""Summarize ignored SHARC receipts; ROADMAP.md remains the sole roadmap.

Counts are known address recovery, not estimated effort or game compatibility.
Fragment/prefix/trace-only evidence is deliberately excluded.
"""
import argparse
import json
from pathlib import Path
from sharc_inventory import inventory


def progress(root, evidence):
    base=inventory(root)
    known={int(x['address'],16) for x in base['functions']+base['address_taken_candidates']}
    known|={int(x,16) for x in json.loads((root/'port/sharc/recovery_targets.json').read_text())['additional_addresses']}
    completed=set();cases=0;suites={}
    for name in ('bits','fields','registers','integer','shift','condition-dispatch','memory','execute','control','transfer','mode','aux','pair','fp','fp-arithmetic','fp-scale','fp-compound','fp-triple','fp-scaled-compound','decode','program','lifecycle','board','reset','board-init','host','upload','upload-control'):
        path=evidence/(name+'-differential.json')
        if not path.exists():continue
        r=json.loads(path.read_text())
        if r['status']!='passed' or r['mismatches'] or r['skipped']:raise ValueError(f'Unqualified receipt: {path}')
        if name=='condition-dispatch':
            conditions={int(x,16) for table in r['tables'] for x in table}
            known|=conditions;entries=conditions|{int(x,16) for x in r['dispatch_entries']}
            count=r['condition_cases']+r['dispatch_cases']
        else:
            count=r['cases']
            if 'entry' in r:entries={int(r['entry'],16)}
            elif name in ('integer','aux'):entries={int(x['entry'],16) for x in r['entries'].values()}
            else:entries={int(x,16) for x in r.get('entries',r.get('cases_by_entry',{}))}
        if entries&completed:raise ValueError(f'Duplicate completed entry in {path}')
        completed|=entries;cases+=count;suites[name]={'entries':len(entries),'cases':count}
    if not completed<=known:raise ValueError(f'Uninventoried entries: {completed-known}')
    integration={}
    for name in ('compute','memory','control','run-compute','memory-board','transfer','runtime','scheduled-runtime','device'):
        path=evidence/(name+'-integration.json')
        if not path.exists():continue
        r=json.loads(path.read_text())
        if r['status']!='passed' or r['mismatches'] or r['skipped']:raise ValueError(f'Unqualified receipt: {path}')
        integration[name]={'cases':r['cases'],'scope':r['scope']}
        if r.get('raw_record_binding'):integration[name]['raw_record_binding']=True
    return {'known_targets':len(known),'reconstructed_entries':len(completed),
        'percent':round(100*len(completed)/len(known),1),'differential_cases':cases,'suites':suites,
        'integration_cases':sum(r['cases'] for r in integration.values()),'integration_suites':integration,
        'remaining_addresses':[f'0x{x:08x}' for x in sorted(known-completed)],
        'scope':'Known addresses; not weighted effort, board integration or playable-game readiness'}


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    ap.add_argument('--evidence-dir',type=Path);args=ap.parse_args()
    print(json.dumps(progress(args.root,args.evidence_dir or args.root/'port/build-sharc'),indent=2))
