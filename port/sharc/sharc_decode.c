#include "sharc_decode.h"

/* All operand encodings in this decoder are group-0 registers. This is the
 * already-recovered 4bcb80 mapping: state + 0xd8 + 4*index. No register content
 * is read while building a record. */
static uint32_t reg(uint32_t state,unsigned index) { return state+0xd8+4*(index&15); }

static uint32_t scalar_handler(uint32_t op) {
    switch(op) {
    case 0:return 0x4bc630;
    case 1:return 0x460f40;case 2:return 0x460fc0;
    case 5:return 0x461040;case 6:return 0x4610c0;
    case 9:return 0x461140;case 0xa:return 0x4611a0;
    case 0x21:return 0x4614e0;case 0x22:return 0x4613e0;
    case 0x25:return 0x4611e0;case 0x26:return 0x461260;
    case 0x29:return 0x4612e0;case 0x2a:return 0x461360;
    case 0x30:return 0x461460;
    case 0x40:return 0x461520;case 0x41:return 0x461560;
    case 0x42:return 0x4615a0;case 0x43:return 0x4615e0;
    case 0x61:return 0x461620;case 0x62:return 0x461660;case 0x63:return 0x4bc240;
    case 0x81:return 0x461700;case 0x82:return 0x4617a0;
    case 0x89:return 0x461980;case 0x8a:return 0x461a40;
    case 0x91:return 0x461840;case 0x92:return 0x4618e0;
    case 0xa1:return 0x461c20;case 0xa2:return 0x461ae0;
    case 0xa5:return 0x461cc0;case 0xad:return 0x4bc200;
    case 0xb0:return 0x461b80;case 0xbd:return 0x461d60;
    case 0xc1:return 0x4bc1b0;case 0xc4:return 0x462340;
    case 0xc5:return 0x4623e0;case 0xc9:return 0x4bc210;
    case 0xca:return 0x462200;case 0xcd:return 0x461f60;
    case 0xd9:return 0x462140;case 0xda:return 0x4622a0;
    case 0xdd:return 0x462000;case 0xe0:return 0x462480;
    case 0xe1:return 0x4bc170;case 0xe2:return 0x4bc130;case 0xe3:return 0x4be1d0;
    case 0x130:return 0x462700;
    default:return 0x4bd520;
    }
}
static uint32_t shift_handler(uint32_t op) {
    switch(op) {
    case 0x200:return 0x4627a0;case 0x204:return 0x462900;
    case 0x208:return 0x462960;case 0x220:return 0x462800;
    case 0x224:return 0x462880;case 0x240:return 0x4bc470;
    case 0x244:return 0x4bc5b0;case 0x248:return 0x4bc420;
    case 0x24c:return 0x4bc510;case 0x264:return 0x4bc560;
    case 0x26c:return 0x4bc4c0;case 0x2c0:return 0x462a20;
    case 0x2c4:return 0x4629c0;case 0x2c8:return 0x462a60;
    case 0x2cc:return 0x4bc3f0;default:return 0;
    }
}
void m2_sharc_decode_compute(uint32_t instruction,uint32_t extension,
    uint32_t state,uint32_t base,uint32_t r[27])
{
    uint32_t op=(instruction>>12)&0x7ff,group,handler=0;
    unsigned x=instruction&15,y=(instruction>>4)&15,z=(instruction>>8)&15;
    unsigned w=(instruction>>12)&15;
    if(extension&1)op=(((instruction&0x3f0000u)|0x800000u)>>14)|(extension<<16);
    group=op>>4;
    r[0x38/4]=reg(state,x);r[0x34/4]=reg(state,y);r[0x3c/4]=reg(state,z);
    if(((group>>4)&7)==7)handler=0x4bc270;
    else if((op&0xfe0)==0x400) {
        /* Accumulator-bank move, not a multiply implementation. */
        if(op&0x10){r[0x34/4]=reg(state,z);r[0x3c/4]=state+0x118+4*w;}
        else {r[0x34/4]=state+0x118+4*w;r[0x3c/4]=reg(state,z);}
        r[1]=0x4bc640;return;
    } else if(group==7 || group==15) {
        r[0x50/4]=reg(state,x);r[0x48/4]=reg(state,y);
        r[0x58/4]=reg(state,z);r[0x5c/4]=reg(state,w);
        r[0x44/4]=base+0x48;r[0x34/4]=base+0x44;r[0x3c/4]=base+0x30;
        r[1]=group==7?0x4bc3a0:0x4bc310;return;
    } else if(group>=0x58 && group<=0x5f) {
        static const uint32_t multi[]={0x4bd4b0,0x4bd440,0x4bd3b0,0x4bd320,
            0x4bd2a0,0x4be220,0x4bd220,0x4bd1a0};
        handler=multi[group-0x58];
    }
    if(handler) {
        r[0x54/4]=reg(state,12+(instruction&3));
        r[0x4c/4]=reg(state,8+((instruction>>2)&3));
        r[0x68/4]=reg(state,4+((instruction>>4)&3));
        r[0x64/4]=reg(state,(instruction>>6)&3);
        r[0x58/4]=reg(state,z);r[0x60/4]=reg(state,w);
        if(handler==0x4bc270)r[0x5c/4]=reg(state,(instruction>>16)&15);
        r[0x44/4]=base+0x48;r[0x34/4]=base+0x44;r[0x3c/4]=base+0x30;
    } else if((op&0x1c6)==0x140)handler=0x4bc600;
    else {
        handler=shift_handler(op);
        if(!handler && op>=0x10200 && op<=0x102cc)handler=shift_handler(op-0x10000);
        if(handler) {
            uint32_t shift_op=op&0xffff;
            if(op>=0x10000) {
                r[0x34/4]=reg(state,x);r[0x38/4]=base+0x1c;
                r[0x3c/4]=shift_op==0x2cc?base+0x30:reg(state,y);
            } else if(shift_op==0x2cc)r[0x3c/4]=base+0x30;
            if(shift_op==0x220 || shift_op==0x224 || shift_op==0x264 || shift_op==0x26c) {
                r[0x40/4]=r[0x34/4];r[0x34/4]=base+0x34;
            }
        } else {
            handler=scalar_handler(op);
            if(op==0xa || op==0x8a)r[0x3c/4]=base+0x30;
        }
    }
    if(handler==0x4bc630 || handler==0x4bd520)r[0x3c/4]=r[0x34/4];
    r[1]=handler;
}
