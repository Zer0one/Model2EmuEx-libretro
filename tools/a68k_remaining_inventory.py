#!/usr/bin/env python3
"""Index unrecovered native dispatch targets against a qualified test receipt.

Reuses the existing ISA-label inventory. Mnemonics are discovery labels, never
permission to substitute Musashi semantics for the original executable.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('inventory',type=Path)
    ap.add_argument('qualification',type=Path)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    inventory=json.loads(args.inventory.read_text())
    qualified=json.loads(args.qualification.read_text())
    assert inventory['original_sha256']==qualified['original_sha256']
    targets={0x478438,0x48b518,0x48b540,0x48b568} # Existing flow group.
    for value in qualified.values():
        if isinstance(value,dict) and isinstance(value.get('targets'),list):
            targets.update(int(t,16) for t in value['targets'])
    assert len(targets)==qualified['dispatch_coverage']['targets']
    rows=inventory['a68k']['target_rows']
    remaining=[row for row in rows if int(row['address'],16) not in targets]
    entries=sum(row['opcode_count'] for row in remaining)
    assert len(remaining)+len(targets)==1667
    assert entries+qualified['dispatch_coverage']['entries']==65536
    families=collections.Counter('/'.join(row['isa_labels']) for row in remaining)
    result=dict(original_sha256=inventory['original_sha256'],qualified_targets=len(targets),
        remaining_targets=len(remaining),remaining_entries=entries,
        targets_by_isa_label=dict(sorted(families.items())),targets=remaining,
        source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in (args.inventory,args.qualification,Path(__file__))},
        limits=['Dispatch identities only, not weighted effort or instruction equivalence.',
                'DISASSEMBLER_DC is an unclassified encoding, not proof the original traps.',
                'Full dispatcher, sound scheduling, state integration and frontend qualification are additional work.'])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='targets'},indent=2))


if __name__=='__main__':main()
