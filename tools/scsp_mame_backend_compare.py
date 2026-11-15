#!/usr/bin/env python3
"""Compare the selectable MAME path with the pinned pre-recovery SCSP source.

Synthetic slots/programs only. Compare PCM, shared sound RAM and common DSP
fields; archive layouts deliberately differ. Temporary builds are removed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

BASE = '724eab3f579fb35dc79912f91470787081ec527e'
SOURCE_HASH = '6689809c6b8a3a6e8bda13b6be1c4917c79fc2fa084f148545aa272630215f10'
DRIVER = r'''
#include <stdio.h>
#include <assert.h>
#include SCSP_SOURCE
#ifdef SELECT_BACKEND
#define D(s) (&(s)->DSP.context)
#else
#define D(s) (&(s)->DSP)
#endif
static uint64_t hash=14695981039346656037ull;
static void bytes(const void *ptr,size_t n) {
    const uint8_t *p=ptr;for(size_t i=0;i<n;i++){hash^=p[i];hash*=1099511628211ull;}
}
static void wr(scsp *s,unsigned addr,unsigned value) {scsp_write16(s,addr,(uint16_t)value,0xffff);}
static unsigned backing(unsigned address) {
#ifdef SELECT_BACKEND
    return address^1u; /* Approved native storage; baseline remains big-endian. */
#else
    return address;
#endif
}
static unsigned matched_input, nonzero;
static void observe(scsp *s,uint8_t *ram) {
    int32_t pcm[128];
    if (matched_input) {
        for (unsigned frame = 0; frame < 64; ++frame) {
            D(s)->MIXS[0] = ((int)frame * 521 - 16384) * 16;
            scsp_render(s, pcm + 2 * frame, 1);
        }
    } else scsp_render(s,pcm,64);
    for (unsigned i=0;i<128;i++) nonzero += pcm[i]!=0;
    bytes(pcm,sizeof pcm);
    /* Compare guest-addressed bytes, not the changed host representation. */
    for(unsigned i=0;i<0x100000;i++)bytes(ram+backing(i),1);
    dsp_t *d=D(s);
#define F(f) bytes(&d->f,sizeof d->f)
    F(RBP);F(RBL);F(COEF);F(MADRS);F(MPRO);F(TEMP);F(MEMS);F(DEC);F(MIXS);F(EXTS);F(EFREG);F(LastStep);
#undef F
    int stopped=d->Stopped;bytes(&stopped,sizeof stopped);
}
int main(int argc, char **argv) {
    matched_input = argc == 2 && !strcmp(argv[1], "matched");
    uint8_t *ram=calloc(1,0x100000);assert(ram);
    for(unsigned c=0;c<64;c++) {
        for(unsigned i=0;i<0x100000;i++)ram[backing(i)]=(uint8_t)(i*73+(i>>8)+c*17);
#ifdef SELECT_BACKEND
        scsp *s=scsp_create(ram,0x100000,0xfffff,NULL,NULL);
#else
        scsp *s=scsp_create(ram,0xfffff,NULL,NULL);
#endif
        assert(s);
#ifdef SELECT_BACKEND
        scsp_set_dsp_backend(s,SCSP_DSP_MAME);
#endif
        wr(s,0x400,15);wr(s,2,0x4000);wr(s,6,31);wr(s,8,0x1f);
        wr(s,0xc,(c*13)&255);wr(s,0x14,c&7);
        wr(s,0x16,((c&31)<<8)|(((c>>3)&7)<<5));
        if (!matched_input) wr(s,0,0x1820|(c&2?0x10:0));
        wr(s,0x700,0x4000);
        wr(s,0x802,0xa800);wr(s,0x804,2);
        wr(s,0x80c,0x1000|(c&1?0x4000:0));wr(s,0x80e,0x8000);
        wr(s,0xbfe,0);observe(s,ram); /* Must remain stopped. */
        wr(s,0xbf0,0);observe(s,ram); /* MAME's historical Start. */
        wr(s,0x700,0x6000);wr(s,0x804,6);observe(s,ram); /* Live program edits. */
        scsp_reset(s);observe(s,ram);
        scsp_destroy(s);
    }
    assert(nonzero);
    printf("%016llx\n",(unsigned long long)hash);free(ram);return 0;
}
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    root = Path(__file__).resolve().parent.parent
    baseline = subprocess.check_output(['git', 'show', f'{BASE}:port/snd/scsp.c'], cwd=root)
    assert hashlib.sha256(baseline).hexdigest() == SOURCE_HASH
    results = {}
    with tempfile.TemporaryDirectory(prefix='model2-dsp-backend-') as tmp:
        work = Path(tmp)
        (work/'baseline.c').write_bytes(baseline)
        (work/'scsp.h').write_bytes(subprocess.check_output(['git','show',f'{BASE}:port/snd/scsp.h'],cwd=root))
        (work/'driver.c').write_text(DRIVER)
        for name, source in [('baseline', work/'baseline.c'), ('selectable', root/'port/snd/scsp.c')]:
            binary = work/name
            command = ['clang', '-O2', '-std=c11', '-I'+str(root/'port/snd'),
                       '-DSCSP_SOURCE="'+str(source)+'"', str(work/'driver.c'), '-lm', '-o', str(binary)]
            if name == 'selectable':
                command += ['-DSELECT_BACKEND', str(root/'port/snd/scsp_dsp_original.c')]
            subprocess.run(command, check=True)
            results[name] = {mode: subprocess.check_output([str(binary), mode], text=True).strip()
                             for mode in ('matched', 'voices')}
    result = dict(baseline_commit=BASE, baseline_source_sha256=SOURCE_HASH, cases=64,
                  sample_frames=64*4*64, fingerprints=results, exact_matched=results['baseline']['matched']==results['selectable']['matched'],
                  scope='Matched MIXS checks DSP PCM, guest RAM and common DSP fields. Whole-voice fingerprints also include the shared ElSemi interpolator.')
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
    assert result['exact_matched']


if __name__ == '__main__':
    main()
