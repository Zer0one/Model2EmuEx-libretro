#!/usr/bin/env python3
"""Compare Super GT 24h's destination pedal bytes with the current SM2 bus.

The caller supplies probes built from the production bridge/board reader and
the reference machine. The reference reads the existing game archive in place.
Cases include every byte position on each pedal, live I/O Type transitions,
simultaneous pressure and invalid/unavailable operator RAM.
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def run(command, rows):
    result=subprocess.run([str(p) for p in command],input=''.join(' '.join(map(str,row))+'\n' for row in rows),
                          text=True,capture_output=True,check=True)
    return [list(map(int,line.split())) for line in result.stdout.splitlines()]


def compare(probe, reference, database, archive):
    cases=[]
    # Native values are A=1, B=3, C=0. The repeat of A checks live handover.
    for io_type, initialized in [(1,1),(3,1),(0,1),(1,1),(0,0),(0,2),(256,1)]:
        for byte in range(256):
            axis=(byte*32767+127)//255
            cases.extend([(axis,8192,io_type,initialized),(8192,axis,io_type,initialized)])
        for a in (0,8192,16384,32767):
            for b in (0,8192,16384,32767):
                cases.append((a,b,io_type,initialized))
    actual=run([probe],cases)
    assert len(actual)==len(cases) and all(len(row)==6 for row in actual)
    expected=run([reference,database,archive],
                 [(row[0],row[1],row[2],case[2],case[3]) for case,row in zip(cases,actual)])
    assert len(expected)==len(cases) and all(len(row)==3 for row in expected)
    for case,row,want in zip(cases,actual,expected):
        assert row[3:]==want, (case,row,want)
        assert row[0]==row[3], 'Steering changed'
    return dict(status='pass',cases=len(cases),channel_comparisons=len(cases)*3,
                io_types={'A':1,'B':3,'C':0},
                missing_ram=True,invalid_signature=True,nonzero_high_byte=True,
                reference_database_sha256=hashlib.sha256(database.read_bytes()).hexdigest())


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('probe',type=Path)
    parser.add_argument('reference',type=Path)
    parser.add_argument('database',type=Path)
    parser.add_argument('archive',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=compare(args.probe,args.reference,args.database,args.archive)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
