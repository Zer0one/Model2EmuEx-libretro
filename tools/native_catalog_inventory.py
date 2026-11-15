#!/usr/bin/env python3
"""Inventory initialized ElSemi game records across every board, without ROMs.

Consumes the existing dump_games.py memory/heap witness and the pinned PE.
Find every occurrence of a native board-string pointer throughout the dumped
image, rather than restricting a scan to known list entries or board types.
Validate record dimensions, rate and every linked ROM node before accepting it.
"""
import argparse, collections, hashlib, importlib.util, json, struct
from pathlib import Path
from original_inventory import OriginalPE
ROOT=Path(__file__).resolve().parents[1]

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('exe',type=Path);ap.add_argument('dump',type=Path)
    ap.add_argument('--source',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    pe=OriginalPE(args.exe)
    image=Path(str(args.dump)+'.mem').read_bytes()
    heap=Path(str(args.dump)+'.heap').read_bytes()
    def read(at,n):
        for base,data in ((0x528000,image),(0x20000000,heap)):
            if base<=at and at+n<=base+len(data):return data[at-base:at-base+n]
        return pe.read(at,n)
    def word(at):return struct.unpack('<I',read(at,4))[0]
    def string(at):
        if not at:return None
        try:data=read(at,96).split(b'\0')[0]
        except ValueError:return None
        return data.decode('ascii') if data and all(32<=c<127 for c in data) else None
    pointers={}
    for section in pe.sections:
        start=section['offset'];raw=pe.data[start:start+section['raw_size']]
        for board in ('Model 2','Model 2A','Model 2B','Model 2C'):
            needle=board.encode()+b'\0';offset=0
            while (offset:=raw.find(needle,offset))>=0:
                pointers[section['address']+offset]=board;offset+=len(needle)
    spec=importlib.util.spec_from_file_location('align',ROOT/'scripts/align-mame-romsets.py')
    align=importlib.util.module_from_spec(spec);spec.loader.exec_module(align)
    mame=align.parse_mame(args.source.read_text());signatures=collections.defaultdict(list)
    for name,g in mame.items():
        signatures[tuple(sorted((f['size'],f['crc']) for f in g['files'] if f['region']=='maincpu'))].append(name)
    records=[]
    for pointer,board in pointers.items():
        cursor=0;needle=struct.pack('<I',pointer)
        while (cursor:=image.find(needle,cursor))>=0:
            at=0x528000+cursor-0x10;cursor+=4
            if at%4:continue
            try:
                width,height=word(at+0x20),word(at+0x24)
                rate=struct.unpack('<f',read(at+0x28,4))[0]
                if not(1<=width<=4096 and 1<=height<=4096 and 30<=rate<=120):continue
                title=string(word(at+4));head=word(at+0x30);count=word(at+0x34)
                if not title or not 1<=count<=512:continue
                node=word(head);seen=set();program=[];region=-1
                while node!=head:
                    if not node or node in seen or len(seen)>=count:raise ValueError('ROM list')
                    seen.add(node);kind=word(node+8)
                    if kind==0:region=word(node+12)&255
                    elif kind==1:
                        if not string(word(node+12)):raise ValueError('ROM name')
                        if region==0:program.append((word(node+20),word(node+24)))
                    elif kind not in (2,3,4,5):raise ValueError('ROM operation')
                    node=word(node)
                if len(seen)!=count or not program:continue
                records.append(dict(record=f'{at:08x}',board=board,title=title,
                    width=width,height=height,fps=rate,rom_operations=count,
                    main_program=sorted(program),mame_matches=signatures.get(tuple(sorted(program)),[])))
            except (ValueError,struct.error):continue
    records.sort(key=lambda r:r['record'])
    assert len({r['record'] for r in records})==len(records)
    result=dict(original_sha256=hashlib.sha256(pe.data).hexdigest(),
        dump_sha256=hashlib.sha256(image).hexdigest(),heap_sha256=hashlib.sha256(heap).hexdigest(),
        counts=dict(collections.Counter(r['board'] for r in records)),records=records)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2)+'\n')
    print('Initialized records:',len(records),result['counts'])
if __name__=='__main__':main()
