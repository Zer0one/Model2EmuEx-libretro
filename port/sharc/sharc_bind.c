#include "sharc_bind.h"
#include "sharc_program.h"
static bool condition(uint32_t target,uint32_t *code) {
    uint32_t scratch[27],i;
    for(i=0;i<32;i++)if(m2_sharc_bind_condition(i,scratch)==target){*code=i;return true;}
    return false;
}
bool m2_sharc_bind_memory(const uint32_t r[27],m2_sharc_word_resolver word,
    void *opaque,m2_sharc_memory_record *out)
{
    m2_sharc_memory_record b={0};
    bool conditional=false;
    unsigned i;
    switch(r[0]) {
    case 0x4bd810:case 0x4bd890:case 0x4bd910:case 0x4bd990:
    case 0x4bdad0:case 0x4bdb10:case 0x4bdb60:case 0x4bdbb0:case 0x4bdc00:
    case 0x4bdc60:case 0x4bdcb0:case 0x4bdd00:case 0x4bdd50:conditional=true;break;
    case 0x4bddb0:case 0x4bde20:case 0x4bdea0:case 0x4bdf20:
    case 0x4bca50:case 0x4bca80:case 0x4bcab0:case 0x4bcac0:case 0x4bd540:
    case 0x4bd650:case 0x4bd680:case 0x4bd6a0:case 0x4bd6c0:case 0x4bd6e0:break;
    default:return false;
    }
    if(conditional && !condition(r[2],&b.condition))return false;
    b.operation=r[1];b.immediate=r[7];b.flags=r[11];
    for(i=0;i<2;i++) {
        b.address[i]=word(opaque,r[3+2*i]);b.step[i]=word(opaque,r[4+2*i]);
        b.data[i]=word(opaque,r[9+i]);b.mirror[i]=word(opaque,r[9+i]-0x80u);
    }
    b.lhs=word(opaque,r[13]);b.rhs=word(opaque,r[14]);b.destination=word(opaque,r[15]);
    *out=b;return true;
}
bool m2_sharc_bind_control(const uint32_t r[27],m2_sharc_word_resolver word,
    void *opaque,m2_sharc_control_record *out)
{
    m2_sharc_control_record b={0};
    bool conditional=true;
    switch(r[0]) {
    case 0x4bd700:case 0x4bd750:case 0x4bd7b0:conditional=false;break;
    case 0x4bcad0:case 0x4bda10:case 0x4bda60:case 0x4be2a0:case 0x4be310:
    case 0x4be380:case 0x4be460:case 0x4be540:case 0x4be610:
    case 0x4be6f0:case 0x4be750:case 0x4be7c0:break;
    default:return false;
    }
    if(conditional && !condition(r[2],&b.condition))return false;
    b.operation=r[1];b.immediate=r[7];b.count=r[8];b.flags=r[11];
    b.value=word(opaque,r[9]);b.address=word(opaque,r[3]);b.step=word(opaque,r[4]);
    b.lhs=word(opaque,r[13]);b.rhs=word(opaque,r[14]);b.destination=word(opaque,r[15]);
    *out=b;return true;
}
