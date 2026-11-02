// ROM-free adaptation of SM2 src/libretro/checks/manxtt_audio.cpp.
// Include the adapter to inspect policy state without exporting diagnostic ABI.
#include "../src/libretro/manxtt_bridge.cpp"
#include <cassert>
#include <iostream>
#include <vector>
extern "C" unsigned m68k_read_memory_8(unsigned);
extern "C" void m68k_write_memory_16(unsigned,unsigned);
static void commit(m2_board &b) {
    uint16_t crc=0xffff;
    for(unsigned i=2;i<0x38;i++) {
        crc^=(uint16_t)b.eeprom.data[i]<<8;
        for(unsigned n=0;n<8;n++)crc=(uint16_t)(crc&0x8000?(crc<<1)^0x1021:crc<<1);
    }
    crc=(uint16_t)~crc;b.eeprom.data[0]=(uint8_t)crc;b.eeprom.data[1]=(uint8_t)(crc>>8);
}
static std::vector<int16_t> advance(unsigned frames=4096) {
    std::vector<int16_t> pcm(frames*2);m2snd_render(cabinet.main,pcm.data(),frames);
    m2lr_manxtt_mix(pcm.data(),frames);return pcm;
}
int main(int argc,char **argv) {
    assert(argc==2);const char *dirs[]={argv[1],nullptr};
    m2_board b{};std::vector<uint8_t> back(0x18000,0xa5),program(512),samples(0x1000);
    const uint8_t initial[]={7,0,0,0xff,0x60,0,0,1};
    memcpy(program.data(),initial,8);program[0x100]=0xfe;program[0x101]=0x60;
    b.game=m2_find_game("manxtt");b.type=1;b.manxtt_audio=1;b.ams_response=0xff;b.back=back.data();
    b.rom.ptr[5]=program.data();b.rom.size[5]=(uint32_t)program.size();
    b.rom.ptr[6]=samples.data();b.rom.size[6]=(uint32_t)samples.size();
    b.sound_uart=m2uart_create(25000000,nullptr,[](void *,uint8_t byte){m2lr_manxtt_command(byte);},nullptr);
    auto *main=m2snd_create(&b);assert(main && b.sound_uart);
    assert(m2lr_manxtt_prepare(&b,main,dirs));
    assert(cabinet.available[1] && cabinet.available[2] && cabinet.aux);
    assert(cabinet.banks[1].size[5]==0x80000 && cabinet.extra.size[5]==0xc0000 && cabinet.extra.size[6]==0x400000);
    b.eeprom.data[2]=0x38;b.eeprom.data[10]=1;commit(b);
    bool changed=false;assert(m2lr_manxtt_update(true,&changed));assert(changed && cabinet.bank==1 && !cabinet.enabled);
    b.eeprom.data[10]=0;m2lr_manxtt_update(true,&changed);assert(!changed && cabinet.bank==1);
    commit(b);const auto before=b.eeprom;
    m2lr_manxtt_update(true,&changed);assert(changed && cabinet.bank==2 && cabinet.enabled);
    assert(!memcmp(&before,&b.eeprom,sizeof before));assert(back.back()==0xa5);
    // A synthetic PCM voice proves the additional native board reaches output.
    int16_t scratch[16];m2snd_run_aux(cabinet.aux,1,scratch);
    assert(m68k_read_memory_8(0x20000)==0 && m68k_read_memory_8(0x40000)==0xff);
    m68k_write_memory_16(0xc40002,0);
    auto reg=[](unsigned index,unsigned value) { m68k_write_memory_16(0xc40004,index);m68k_write_memory_16(0xc40000,value); };
    reg(0,0);reg(1,0);reg(2,0);reg(3,0);reg(5,1);reg(4,0x80);
    const auto output=advance();assert(std::any_of(output.begin(),output.end(),[](auto v){return v!=0;}));
    // Full bidirectional I8251, including pending transmitter serialization.
    m2uart_write(b.sound_uart,1,0x4e);m2uart_write(b.sound_uart,1,0x05);
    m2uart_receive(b.sound_uart,0xac);assert(m2uart_read(b.sound_uart,1)&2);assert(m2uart_read(b.sound_uart,0)==0xac);
    m2snd_render(main,scratch,0);m68k_write_memory_16(0x100406,0xbc);
    std::array<int16_t,28> midi_audio{};m2snd_render(main,midi_audio.data(),14);
    assert(m2uart_read(b.sound_uart,0)==0xbc); // Real SCSP MIDI-out register.
    m2snd_run_aux(cabinet.aux,1,scratch);
    m68k_write_memory_16(0xc20002,0x4e);m68k_write_memory_16(0xc20002,0x05);
    m2uart_write(b.sound_uart,0,0xae);m2uart_run(b.sound_uart,7999);
    assert(!(m68k_read_memory_8(0xc20003)&2));m2uart_run(b.sound_uart,1);
    m2snd_run_aux(cabinet.aux,1,scratch);assert(m68k_read_memory_8(0xc20001)==0xae);
    m68k_write_memory_16(0xc20000,0x9a);advance(100);
    assert(m2uart_read(b.sound_uart,0)==0x9a); // M1 transmitter returns to host.
    std::vector<uint8_t> state(2*1024*1024);uint8_t header[20]{};m2lr_manxtt_state_header(header);
    assert(m2lr_manxtt_state_compatible(header));
    auto save=[&] { m2_state a{state.data(),state.size(),0,M2_STATE_SAVE,0};m2snd_state_archive(main,&a);m2lr_manxtt_state_archive(&a);assert(!a.failed);return a.pos; };
    auto used=save();auto expected=advance();
    m2lr_manxtt_update(false,&changed);assert(changed && cabinet.bank==0 && cabinet.enabled);
    m2_state check{state.data(),used,0,M2_STATE_CHECK,0};m2snd_state_archive(main,&check);m2lr_manxtt_state_archive(&check);assert(!check.failed && check.pos==used);
    m2lr_manxtt_state_bind(header);
    m2_state load{state.data(),used,0,M2_STATE_LOAD,0};m2snd_state_archive(main,&load);m2lr_manxtt_state_archive(&load);
    assert(!load.failed && cabinet.bank==2 && cabinet.enabled);assert(advance()==expected);
    m2lr_manxtt_gains(0,0,0);advance(100);const auto muted=advance();
    assert(std::all_of(muted.begin(),muted.end(),[](auto v){return v==0;}));
    header[8]^=1;assert(!m2lr_manxtt_state_compatible(header));header[8]^=1;
    m2lr_manxtt_state_bind(nullptr);assert(cabinet.bank==0 && b.ams_response==0xff);
    m2lr_manxtt_destroy();m2snd_destroy(main);
    // Missing optional regions retain selected-set audio and emit SM2 notices.
    const char *empty[]={"/nonexistent/manxtt-fixture",nullptr};main=m2snd_create(&b);
    assert(m2lr_manxtt_prepare(&b,main,empty));assert(!cabinet.aux);
    assert(std::string(m2lr_manxtt_update(true,&changed)).find("matching cabinet audio ROMs unavailable")!=std::string::npos);
    assert(cabinet.bank==0 && !cabinet.enabled);
    assert(std::string(m2lr_manxtt_update(true,&changed)).find("additional sound ROMs unavailable")!=std::string::npos);
    m2lr_manxtt_destroy();m2snd_destroy(main);m2uart_destroy(b.sound_uart);
    std::cout<<"PASS: Manx TT banks, unfinished EEPROM, native PCM mix, gains, I8251, sample-exact state continuation, ROM identity, legacy reset, optional-ROM fallback; no NVRAM writes\n";
}
