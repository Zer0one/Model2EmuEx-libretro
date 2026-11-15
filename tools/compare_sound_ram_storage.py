#!/usr/bin/env python3
"""Compare isolated GL state runs around a sound-RAM byte-order conversion.

Normalize only the explicitly supplied RAM interval, excluding the 128-byte
state header whose schema/checksum must change. This is an evidence tool, never
a state migration or loader. Input captures are read-only.
"""
import argparse,hashlib,json,re
from pathlib import Path

def compare(before,after,offset,size):
    a=(before/'core.state').read_bytes();b=(after/'core.state').read_bytes()
    assert len(a)==len(b) and offset>=128 and size%2==0 and offset+size<=len(b)
    span=b[offset:offset+size];swapped=bytearray(span)
    swapped[::2]=span[1::2];swapped[1::2]=span[::2]
    normalized=b[128:offset]+swapped+b[offset+size:]
    pcm=[]
    for path in (before,after):
        pcm.append(re.search(r'PCM CRC ([0-9a-f]+) \((\d+) frames\)',(path/'run.log').read_text()).group(0))
    result={'normalized_state_payload_exact':a[128:]==normalized,'normalization_offset':offset,'normalization_bytes':size,
            'continuation_pcm':pcm,'continuation_pcm_exact':pcm[0]==pcm[1],
            'captured_pcm_exact':(before/'core.pcm').read_bytes()==(after/'core.pcm').read_bytes(),
            'rendered_continuation_exact':(before/'continued.rgb').read_bytes()==(after/'continued.rgb').read_bytes(),
            'state_before_sha256':hashlib.sha256(a).hexdigest(),'state_after_sha256':hashlib.sha256(b).hexdigest(),
            'before':str(before),'after':str(after)}
    for field in ('normalized_state_payload_exact','continuation_pcm_exact','captured_pcm_exact','rendered_continuation_exact'):
        assert result[field],field
    return result

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--before',type=Path,required=True);ap.add_argument('--after',type=Path,required=True)
    ap.add_argument('--ram-offset',type=lambda s:int(s,0),required=True)
    ap.add_argument('--ram-size',type=lambda s:int(s,0),default=0x100000)
    ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    result=compare(a.before,a.after,a.ram_offset,a.ram_size)
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
