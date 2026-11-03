// Libretro ownership reuses SM2's transport; the machine receives only C hooks.
#include "net_bridge.h"
#include "sm2/netpacket.h"
#include <cstring>
#include <cstdio>
namespace {
sm2::libretro::NetpacketTransport transport;
retro_environment_t environment;
retro_log_printf_t logger;
int ready(void *) { return transport.ready(); }
void send(void *,const uint8_t *p,size_t n) { transport.send({p,n}); }
size_t receive(void *,uint8_t *p,size_t capacity) {
    auto frame=transport.recv();
    if(!frame || frame->size()>capacity)return 0;
    std::memcpy(p,frame->data(),frame->size());return frame->size();
}
void clear(void *) { transport.reset(); }
}
static void message(const char *text,retro_log_level level) {
    if(logger)logger(level,"[Model2EmuEx] %s\n",text);
    else std::fprintf(stderr,"[Model2EmuEx] %s\n",text);
    if(!environment)return;
    unsigned version=0;
    if(environment(RETRO_ENVIRONMENT_GET_MESSAGE_INTERFACE_VERSION,&version) && version>=1) {
        retro_message_ext message{text,5000,level==RETRO_LOG_ERROR?2u:1u,level,RETRO_MESSAGE_TARGET_OSD,RETRO_MESSAGE_TYPE_NOTIFICATION,-1};
        if(environment(RETRO_ENVIRONMENT_SET_MESSAGE_EXT,&message))return;
    }
    retro_message message{text,300};environment(RETRO_ENVIRONMENT_SET_MESSAGE,&message);
}
extern "C" void m2lr_net_message(const char *text) { message(text,RETRO_LOG_WARN); }
extern "C" void m2lr_net_error(const char *text) { message(text,RETRO_LOG_ERROR); }
extern "C" void m2lr_net_notice(const char *text) { message(text,RETRO_LOG_INFO); }
extern "C" void m2lr_net_init(retro_environment_t env,retro_log_printf_t log) {
    environment=env;logger=log;
    (void)sm2::libretro::register_netpacket_interface(env,log);
}
extern "C" void m2lr_net_shutdown() {
    sm2::libretro::shutdown_netpacket_interface();environment=nullptr;logger=nullptr;
}
extern "C" void m2lr_net_configure(const char *game,unsigned cabinets) {
    const std::string_view name(game);
    // Different Power Sled programs occupy distinct roles in one SM2 roster.
    const unsigned role=name=="powsledm"?1:name=="powsledr"?2:name=="powsled"?3:0;
    transport.configure(role?"powsled":name,cabinets,role);
    if(!sm2::libretro::netpacket_interface_supported())
        m2lr_net_message("Frontend Netpacket is unavailable; linked cabinets will wait for a supported frontend.");
}
extern "C" void m2lr_net_offline() { sm2::libretro::set_netpacket_offline(); }
extern "C" void m2lr_net_pump() { (void)transport.ready(); }
extern "C" m2_link_transport m2lr_net_transport() { return {nullptr,ready,send,receive,clear}; }
