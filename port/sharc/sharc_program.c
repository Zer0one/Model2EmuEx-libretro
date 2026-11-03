#include "sharc_program.h"
#include "sharc_decode.h"
#include "sharc_registers.h"
#include "sharc_bits.h"
#include <string.h>

/* Original instruction-condition table, not the loop-condition table. */
uint32_t m2_sharc_bind_condition(uint32_t code,uint32_t r[27])
{
    static const uint32_t targets[]={
        0x4bca10,0x4bc9f0,0x4bc9d0,0x4bc9c0,0x4bc9b0,0x4bc990,0x4bc980,0x4bc960,
        0x4bc940,0x4bc920,0x4bc900,0x4bc8e0,0x4bc8c0,0x4bc8a0,0x4bc890,0x4bc870,
        0x4bc850,0x4bc830,0x4bc810,0x4bc7f0,0x4bc7d0,0x4bc7b0,0x4bc790,0x4bc770,
        0x4bc750,0x4bc720,0x4bc6f0,0x4bc6d0,0x4bc6b0,0x4bc690,0x4bc680,0x4bca30};
    r[2]=targets[code&31];return r[2];
}
static uint32_t word16(const uint8_t *p) { return p[0]|((uint32_t)p[1]<<8); }
static uint32_t relative6(uint32_t hi,uint32_t mid) {
    return m2_sharc_extend_immediate(((hi&1)<<5)|(mid>>11),6);
}
static uint32_t immediate12(uint32_t lo,uint32_t mid) {
    return m2_sharc_extend_immediate(((lo>>5)|(mid&0x7800))>>3,12);
}
static void decode_one(const uint8_t *p,uint32_t pc,uint32_t state,uint32_t fixed,
    uint32_t base,uint32_t r[27])
{
    uint32_t lo=word16(p),mid=word16(p+2),hi=word16(p+4),raw=lo|(mid<<16);
    uint32_t bank,offset,sub,selection;
    unsigned compute=0,condition=0,extension=0;
    r[11]&=0xffff0000u; /* Original writes WORD, preserving the high half. */
#define REG(code) m2_sharc_register_token(state,base,r,(uint8_t)(code))
#define DAG(off,index) (fixed+(off)+4*(index))
    switch(hi>>13) {
    case 0:
        sub=(hi>>8)&31;
        switch(sub) {
        case 0:r[0]=0x4bca40;break;
        case 1:r[0]=0x4bcb50;compute=condition=1;break;
        case 2:r[0]=0x4bcb50;r[7]=immediate12(lo,mid);extension=1;compute=condition=1;break;
        case 4:
            bank=(hi&0x40)?8:0;
            r[3]=DAG(0x138,((mid>>14)|(hi*4&7))+bank);
            r[4]=DAG(0x178,((mid>>11)&7)+bank);
            r[0]=0x4bdad0;compute=condition=1;break;
        case 6:case 7:
            if(hi&0x80)r[0]=(mid&0x400)?0x4be6f0:0x4bda10;
            else {
                static const uint32_t jump[]={0x4bcad0,0x4be7c0,0x4bda60,0x4be750};
                r[0]=jump[((mid>>10)&1)|((hi>>5)&2)];
            }
            r[7]=raw&0xffffff;
            if(sub==7)r[7]=m2_sharc_extend_immediate(r[7],24)+pc;
            condition=1;break;
        case 8:case 9:
            r[11]|=((hi>>5)&6)|((mid>>10)&1);
            if(sub==8) {
                r[0]=(mid&0x200)?0x4be460:0x4be610;
                r[3]=DAG(0x158,(mid>>14)+4*(hi&1));r[4]=DAG(0x198,(mid>>11)&7);
            } else {r[0]=(mid&0x200)?0x4be380:0x4be540;r[7]=relative6(hi,mid)+pc;}
            compute=condition=1;break;
        case 10:case 11:
            r[11]|=((mid>>10)&1)|((mid>>7)&2);
            r[0]=(mid&0x200)?0x4be2a0:0x4be310;compute=condition=1;break;
        case 12:case 13:case 14:
            offset=m2_sharc_extend_immediate(raw&0xffffff,24);r[7]=pc+offset;
            if(sub==12){r[8]=((hi&255)<<8)|(mid>>8);r[0]=0x4bd7b0;}
            else {r[9]=REG(sub==13?hi:hi>>1);r[0]=sub==13?0x4bd750:0x4bd700;}
            if(sub==14)r[7]|=(hi&0x3e)<<23;
            else r[7]|=offset==1?0x40000000u:offset==2?0x80000000u:0xc0000000u;
            break;
        case 15:r[7]=raw;r[0]=0x4bcac0;r[9]=REG(hi);break;
        case 16:case 17:case 18:case 19:
            r[7]=raw;r[0]=(hi&0x100)?0x4bd6c0:0x4bd6e0;r[9]=REG(hi);break;
        case 20: {
            static const uint32_t bitop[]={0x4bd5d0,0x4bd550,0x4bcab0,0x4bcac0,
                0x4bca80,0x4bca50,0x4bcac0,0x4bcac0};
            r[7]=raw;r[0]=bitop[(hi>>5)&7];r[9]=REG((hi&15)|0x70);break;
        }
        case 22:r[7]=raw;r[0]=0x4bd540;r[3]=DAG(0x138,(hi&7)+((hi&0x40)?8:0));break;
        default:break; /* Original leaves handler/other fields uninitialized. */
        }
        break;
    case 1: {
        static const uint32_t dual[]={0x4bdf20,0x4bdea0,0x4bde20,0x4bddb0};
        r[0]=dual[((hi>>5)&1)|((hi>>11)&2)];
        r[3]=DAG(0x138,(hi>>9)&7);r[4]=DAG(0x178,(hi>>6)&7);
        r[5]=DAG(0x158,(mid>>14)+4*(hi&1));r[6]=DAG(0x198,(mid>>11)&7);
        r[9]=REG((hi>>1)&15);r[10]=REG((mid>>7)&15);
        compute=1;condition=2;break;
    }
    case 2: {
        static const uint32_t transfer[]={0x4bdc60,0x4bdd00,0x4bdcb0,0x4bdd50};
        bank=(hi&1)?8:0;selection=((hi>>11)&2)|(mid>>15);
        r[0]=transfer[selection];r[3]=DAG(0x138,((hi>>9)&7)+bank);
        /* Unlike other memory forms, this encoding passes the full byte to
         * 4bcb80. Keep special registers and scratch fall-through reachable. */
        r[4]=DAG(0x178,((hi>>6)&7)+bank);r[9]=REG(mid>>7);
        compute=condition=1;break;
    }
    case 3:
        if(!(hi&0x1000)) {
            static const uint32_t transfer[]={0x4bdb10,0x4bdbb0,0x4bdb60,0x4bdc00};
            bank=(hi&0x100)?8:0;r[0]=transfer[((hi>>5)&2)|((hi>>7)&1)];
            r[3]=DAG(0x138,((hi>>9)&7)+bank);r[7]=relative6(hi,mid);
            r[9]=REG((mid>>7)&15);condition=1;
        } else {
            r[0]=0x4bcb10;r[9]=REG(mid>>7);r[10]=REG(hi>>4);condition=3;
        }
        compute=1;break;
    case 4:
        if(hi&0x1000) {
            bank=(hi&0x20)?8:0;r[7]=raw;r[3]=DAG(0x138,((hi>>9)&7)+bank);
            r[4]=DAG(0x178,((hi>>6)&7)+bank);r[0]=0x4bd650;
        } else {
            bank=(hi&1)?8:0;r[0]=(mid&0x8000)?0x4bdd50:0x4bdcb0;
            r[3]=DAG(0x138,((hi>>9)&7)+bank);r[4]=DAG(0x178,((hi>>6)&7)+bank);
            r[9]=REG((mid>>7)&15);r[7]=immediate12(lo,mid);extension=1;compute=condition=1;
        }
        break;
    case 5:
        bank=(hi&0x1000)?8:0;r[7]=raw;r[9]=REG(hi);
        r[3]=DAG(0x138,((hi>>9)&7)+bank);r[0]=(hi&0x100)?0x4bd680:0x4bd6a0;break;
    case 6:
        r[0]=(hi&0x1000)?0x4bd890:0x4bd990;
        r[3]=DAG(0x138,(hi>>9)&15);r[4]=DAG(0x178,(hi>>6)&15);
        r[5]=DAG(0x158,(mid>>14)+4*(hi&1));r[6]=DAG(0x198,(mid>>11)&15);
        r[9]=REG((mid>>7)&15);compute=condition=1;break;
    case 7:
        r[0]=(hi&0x1000)?0x4bd810:0x4bd910;
        r[3]=DAG(0x138,(hi>>9)&15);r[4]=DAG(0x178,(hi>>6)&15);
        r[7]=relative6(hi,mid)+pc;r[9]=REG((mid>>7)&15);compute=condition=1;break;
    }
    if(compute)m2_sharc_decode_compute(raw,extension,state,base,r);
    if(condition)m2_sharc_bind_condition(condition==2?31:condition==3?(mid>>15)|(hi*2):hi>>1,r);
#undef REG
#undef DAG
}
void m2_sharc_decode_program(const uint8_t *source,uint32_t bytes,uint32_t state,
    uint32_t fixed,m2_sharc_program *p,const m2_sharc_program_memory *memory)
{
    uint32_t index;
    p->count=bytes/6;
    if(p->allocation_token)memory->release(memory->opaque,p->allocation,p->allocation_token);
    p->allocation=memory->allocate(memory->opaque,p->count*108,&p->allocation_token);
    p->program_base=p->allocation_token-0xd80000u;p->current_record=p->allocation_token;
    for(index=0;index<p->count;index++) {
        decode_one(source+index*6,0x20000+index,state,fixed,p->current_record,p->allocation+index*27);
        p->current_record+=108;
    }
}
bool m2_sharc_program_matches(const uint8_t *source,const void *records,
    uint32_t count,uint32_t state,uint32_t fixed,uint32_t token)
{
    const uint8_t *saved=records;
    for(uint32_t i=0;i<count;i++) {
        uint32_t rebuilt[27];
        /* Seed with saved words so native WORD writes, unused allocator bits
         * and runtime scratch survive. Only decoder-owned bits are checked. */
        memcpy(rebuilt,saved+i*108,108);
        decode_one(source+i*6,0x20000+i,state,fixed,token+i*108,rebuilt);
        if(memcmp(rebuilt,saved+i*108,108))return false;
    }
    return true;
}
