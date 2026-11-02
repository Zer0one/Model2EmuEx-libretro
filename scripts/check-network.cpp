// Adapted from SM2 src/libretro/checks/netpacket.cpp (BSD-3-Clause).
// SPDX-License-Identifier: BSD-3-Clause
#include "netpacket.h"

#include "m2/m2link.h"
#include <cstring>

#include <algorithm>
#include <array>
#include <cstdio>
#include <deque>
#include <memory>
#include <optional>
#include <span>
#include <stdexcept>
#include <vector>

using namespace sm2;

namespace {

void check(bool okay, const char* message)
{
    if (!okay) throw std::runtime_error(message);
}

retro_netpacket_callback* captured_callbacks = nullptr;
std::vector<u8> sent_packet;
int sent_flags = 0;
u16 sent_peer = 0xffff;

bool environment(unsigned command, void* data)
{
    if (command != RETRO_ENVIRONMENT_SET_NETPACKET_INTERFACE) return false;
    captured_callbacks = static_cast<retro_netpacket_callback*>(data);
    return true;
}

void RETRO_CALLCONV send_packet(int flags, const void* data, std::size_t size,
                                u16 client_id)
{
    sent_flags = flags;
    sent_peer = client_id;
    const auto* bytes = static_cast<const u8*>(data);
    sent_packet.assign(bytes, bytes + size);
}

std::vector<u8> begin_handshake(libretro::NetpacketTransport& transport,
                                u16 local_id, unsigned cabinet_count)
{
    transport.configure("daytona", cabinet_count);
    captured_callbacks->start(local_id, send_packet, nullptr);
    if (local_id == 0)
        for (u16 peer = 1; peer < cabinet_count; ++peer)
            check(captured_callbacks->connected(peer), "Configured cabinet was rejected");
    check(!transport.ready(), "Cabinet became ready before peer hellos arrived");
    check(sent_peer == RETRO_NETPACKET_BROADCAST,
          "Handshake hello was not broadcast to all cabinets");
    return sent_packet;
}

void feed_hello(const std::vector<u8>& hello, u16 sender)
{
    captured_callbacks->receive(hello.data(), hello.size(), sender);
}

void check_host_adapter()
{
    libretro::NetpacketTransport transport;
    const std::vector<u8> hello = begin_handshake(transport, 0, 4);
    feed_hello(hello, 1);
    feed_hello(hello, 2);
    check(!transport.ready(), "Host became ready with an incomplete roster");
    feed_hello(hello, 3);
    check(transport.ready(), "Host did not become ready with four cabinets");
    // Frontend lobby capacity is independent of the current machine total.

    const std::array<u8, 4> payload{0xff, 4, 0, 0};
    transport.send(payload);
    check(sent_peer == 1, "Host frame was not addressed to its ring successor");
    check((sent_flags & RETRO_NETPACKET_RELIABLE) != 0,
          "Communication board frame was not reliable");
    const std::vector<u8> frame = sent_packet;

    captured_callbacks->receive(frame.data(), frame.size(), 2);
    check(!transport.recv(), "Host accepted a frame from a non-predecessor cabinet");
    captured_callbacks->receive(frame.data(), frame.size(), 3);
    const auto received = transport.recv();
    check(received && *received == std::vector<u8>(payload.begin(), payload.end()),
          "Host did not receive the predecessor's communication frame");

    captured_callbacks->disconnected(2);
    check(!transport.ready(), "Disconnected roster remained ready");
    captured_callbacks->stop();
}

void check_client_adapter()
{
    libretro::NetpacketTransport transport;
    const std::vector<u8> hello = begin_handshake(transport, 2, 4);
    feed_hello(hello, 0);
    feed_hello(hello, 1);
    feed_hello(hello, 3);
    check(transport.ready(), "Client did not build the four-cabinet roster");

    const std::array<u8, 3> payload{0xfc, 1, 0};
    transport.send(payload);
    check(sent_peer == 3, "Client frame was not addressed to its ring successor");
    const std::vector<u8> frame = sent_packet;
    captured_callbacks->receive(frame.data(), frame.size(), 1);
    const auto received = transport.recv();
    check(received && *received == std::vector<u8>(payload.begin(), payload.end()),
          "Client did not receive its predecessor's communication frame");
    captured_callbacks->stop();
}

void check_nine_cabinet_capacity()
{
    libretro::NetpacketTransport transport;
    const std::vector<u8> hello = begin_handshake(transport, 0, 9);
    for (u16 peer = 1; peer < 9; ++peer) feed_hello(hello, peer);
    check(transport.ready(), "Nine-cabinet roster did not become ready");
    check(!captured_callbacks->connected(9), "A tenth cabinet was accepted");
    captured_callbacks->stop();
}

void check_mismatched_settings()
{
    libretro::NetpacketTransport transport;
    std::vector<u8> hello = begin_handshake(transport, 0, 2);
    hello[6] = 3;
    captured_callbacks->receive(hello.data(), hello.size(), 1);
    check(!transport.ready(), "Mismatched cabinet count completed the handshake");
    hello[6] = 2;
    captured_callbacks->receive(hello.data(), hello.size(), 1);
    check(transport.ready(), "Temporary cabinet-count mismatch blocked recovery");
    captured_callbacks->stop();
}

void check_burst_order_and_capacity()
{
    libretro::NetpacketTransport transport;
    const auto hello = begin_handshake(transport, 0, 2);
    feed_hello(hello, 1);
    check(transport.ready(), "Burst test roster did not become ready");
    for (unsigned index = 0; index < 512; ++index) {
        const std::array<u8, 2> payload{static_cast<u8>(index),
                                        static_cast<u8>(index >> 8)};
        transport.send(payload);
        captured_callbacks->receive(sent_packet.data(), sent_packet.size(), 1);
    }
    for (unsigned index = 0; index < 512; ++index) {
        const auto frame = transport.recv();
        check(frame && frame->size() == 2 && (*frame)[0] == static_cast<u8>(index)
                  && (*frame)[1] == static_cast<u8>(index >> 8),
              "Burst frame was lost or reordered");
    }
    check(!transport.recv(), "Burst left unexpected frames queued");

    for (unsigned index = 0; index < 1025; ++index) {
        const std::array<u8, 1> payload{static_cast<u8>(index)};
        transport.send(payload);
        captured_callbacks->receive(sent_packet.data(), sent_packet.size(), 1);
    }
    check(!transport.ready(), "Queue overflow did not stop the linked session");
    transport.configure("daytona", 2);
    feed_hello(hello, 1);
    check(transport.ready(), "Reconfigured session did not recover after overflow");
    captured_callbacks->stop();
}

void check_early_frames_do_not_block_roster()
{
    libretro::NetpacketTransport transport;
    const auto hello = begin_handshake(transport, 2, 3);
    std::vector<u8> frame = hello;
    frame[5] = 2;
    frame[12] = 1;
    frame.push_back(0xaa);
    for (unsigned index = 0; index < 1400; ++index)
        captured_callbacks->receive(frame.data(), frame.size(), 1);
    feed_hello(hello, 0);
    feed_hello(hello, 1);
    check(transport.ready(), "Early peer frames prevented the local roster from forming");
    check(!transport.recv(), "Early peer frames leaked into the completed ring");
    captured_callbacks->stop();
}

void check_repeated_hello_does_not_overflow()
{
    libretro::NetpacketTransport transport;
    auto hello = begin_handshake(transport, 2, 3);
    for (u8 type : {u8{1}, u8{3}}) {
        hello[5] = type;
        for (unsigned index = 0; index < 1400; ++index)
            feed_hello(hello, 0);
    }
    feed_hello(hello, 1);
    check(transport.ready(), "Repeated peer hellos filled the pending queue");
    captured_callbacks->stop();
}

void check_mismatched_game()
{
    libretro::NetpacketTransport transport;
    std::vector<u8> hello = begin_handshake(transport, 0, 2);
    hello[8] ^= 1;
    captured_callbacks->receive(hello.data(), hello.size(), 1);
    check(!transport.ready(), "Mismatched game completed the handshake");
    captured_callbacks->stop();
}

void check_known_peer_restarts()
{
    libretro::NetpacketTransport transport;
    auto request = begin_handshake(transport, 0, 2);
    check(request[5] == 3, "Waiting cabinet did not request peer identities");
    feed_hello(request, 1);
    check(transport.ready(), "Restart test roster did not form");
    auto reply = sent_packet;
    check(reply[5] == 1, "Identity request did not receive an ordinary reply");

    sent_packet.clear();
    feed_hello(reply, 1);
    check(transport.ready() && sent_packet.empty(),
          "Known peer reply triggered a broadcast echo");
    for (unsigned i = 0; i < 1400; ++i) feed_hello(request, 1);
    check(transport.ready() && !sent_packet.empty() && sent_packet[5] == 1,
          "Known peer restart request was ignored or overflowed");

    transport.configure("daytona", 2);
    check(!transport.ready(), "Reconfigured cabinet retained its old roster");
    feed_hello(reply, 1);
    check(transport.ready(), "Restarting cabinet rejected known peer identity");
    captured_callbacks->stop();
}

void check_peer_reconfiguration_and_reset_queue()
{
    libretro::NetpacketTransport transport;
    auto hello=begin_handshake(transport,0,2);feed_hello(hello,1);
    check(transport.ready(),"Initial topology");
    auto wrong=hello;wrong[6]=3;feed_hello(wrong,1);
    check(!transport.ready(),"Changed peer kept a stale ready roster");
    feed_hello(hello,1);check(transport.ready(),"Peer did not recover its compatible topology");
    const std::array<u8,3> payload{2,7,8};transport.send(payload);
    auto frame=sent_packet;captured_callbacks->receive(frame.data(),frame.size(),1);
    transport.reset();check(!transport.recv(),"Machine reset retained an unprocessed old frame");
    check(transport.ready(),"Queue reset closed the lobby");
    captured_callbacks->stop();
}

void check_netpacket_adapter()
{
    check(libretro::register_netpacket_interface(environment, nullptr),
          "Frontend rejected Netpacket registration");
    check(captured_callbacks != nullptr, "Netpacket callbacks were not registered");
    check_host_adapter();
    check_client_adapter();
    check_nine_cabinet_capacity();
    check_mismatched_settings();
    check_burst_order_and_capacity();
    check_early_frames_do_not_block_roster();
    check_repeated_hello_does_not_overflow();
    check_mismatched_game();
    check_known_peer_restarts();
    check_peer_reconfiguration_and_reset_queue();
    libretro::shutdown_netpacket_interface();
}

}
void check_active_lobby_reconfiguration()
{
    libretro::NetpacketTransport transport;
    libretro::set_netpacket_offline();
    captured_callbacks->start(0, send_packet, nullptr);
    check(captured_callbacks->connected(1), "Offline lobby rejected a waiting client");
    transport.configure("lobby-lifecycle", 2);
    check(!transport.ready(), "New configuration reused stale frames/roster");
    auto hello = sent_packet;
    captured_callbacks->receive(hello.data(), hello.size(), 1);
    check(transport.ready(), "Existing client not retained on Resume");
    transport.reset();
    check(transport.ready(), "Machine reset destroyed the active frontend session");
    libretro::set_netpacket_offline();
    check(captured_callbacks->connected(2), "Loopback transition lost lobby capacity");
    transport.configure("lobby-lifecycle", 3);
    (void)transport.ready(); hello = sent_packet;
    captured_callbacks->receive(hello.data(), hello.size(), 1);
    check(!transport.ready(), "Staggered setup became ready before the third cabinet");
    captured_callbacks->receive(hello.data(), hello.size(), 2);
    check(transport.ready(), "Staggered setup did not recover without a new start callback");
    transport.configure("lobby-lifecycle", 2);
    (void)transport.ready(); hello = sent_packet;
    captured_callbacks->receive(hello.data(), hello.size(), 1);
    check(transport.ready(), "Reduced total discarded a connected frontend client");
    captured_callbacks->stop();

}
namespace {

struct Node;
struct Bus { std::vector<std::deque<std::vector<u8>>> packets; };
struct Node { m2_board board{}; m2_link link{}; std::vector<u8> ram=std::vector<u8>(0x18000);Bus *bus;unsigned index;bool ready=true; };
int ready(void *p) {return static_cast<Node*>(p)->ready;}
void send(void *p,const uint8_t *bytes,size_t size) {
 auto &n=*static_cast<Node*>(p);n.bus->packets[(n.index+1)%n.bus->packets.size()].emplace_back(bytes,bytes+size);
}
size_t receive(void *p,uint8_t *bytes,size_t capacity) {
 auto &n=*static_cast<Node*>(p);auto &q=n.bus->packets[n.index];if(q.empty())return 0;
 auto frame=std::move(q.front());q.pop_front();check(frame.size()<=capacity,"Native packet exceeded capacity");
 std::memcpy(bytes,frame.data(),frame.size());return frame.size();
}
void clear(void *p) {auto &n=*static_cast<Node*>(p);n.bus->packets[n.index].clear();}
void check_native_ring(unsigned total) {
 Bus bus;bus.packets.resize(total);std::vector<std::unique_ptr<Node>> nodes;
 for(unsigned i=0;i<total;i++) {
  auto n=std::make_unique<Node>();n->bus=&bus;n->index=i;n->board.zshared=n->ram.data();
  n->board.net_enabled=1;n->board.net_reg0=1;n->board.net_reg2=i==0;
  m2link_init(&n->link,total,{n.get(),ready,send,receive,clear});nodes.push_back(std::move(n));
 }
 auto step=[&] {
  for(auto &n:nodes)std::memset(n->ram.data()+0xa000,int(n->index+0x41),0xe00);
  for(auto &n:nodes)m2link_frame(&n->link,&n->board);
 };
 for(unsigned t=0;t<120;t++)step();
 for(unsigned i=0;i<total;i++) {
  auto &n=*nodes[i];check(n.link.state==3,"Native ring failed to establish");
  check(n.ram[0x8003]==total && n.ram[0x8002]==(i==0?1:total-i+1),"Native ID/count differs from m2net");
  check(n.ram[0xa1c0]==0x41+(i+total-1)%total,"Native predecessor block not delivered");
 }
 // Restart each local protocol independently, retaining the other machines.
 for(unsigned reset=0;reset<total;reset++) {
  m2link_reset(&nodes[reset]->link);
  for(unsigned t=0;t<90;t++)step();
  for(auto &n:nodes)check(n->link.state==3,"Staggered machine restart did not recover");
 }
 nodes[1]->ready=false;step();check(nodes[1]->ram[0x8000]==0,"Disconnected board still linked");
 nodes[1]->ready=true;for(unsigned t=0;t<90;t++)step();
 for(auto &n:nodes)check(n->link.state==3,"Reconnect failed");
 // No master must never establish a ring.
 for(auto &n:nodes){m2link_reset(&n->link);n->board.net_reg2=0;}
 for(unsigned t=0;t<60;t++)step();for(auto &n:nodes)check(n->link.state==1,"No-master topology was invented");
}
void check_local_loopback() {
 Node n;n.board.zshared=n.ram.data();n.board.net_enabled=M2_NET_LOOPBACK;
 n.board.net_reg0=1;n.board.net_reg2=1;
 m2link_init(&n.link,1,{});m2link_frame(&n.link,&n.board);
 check(n.link.state==3 && n.ram[0x8002]==1 && n.ram[0x8003]==1,"Local master did not establish one node");
 std::memset(n.ram.data()+0xa000,0x6d,0xe00);auto heartbeat=n.board.net_reg2;
 m2link_frame(&n.link,&n.board);
 check(n.ram[0xa1c0]==0x6d && n.board.net_reg2==(heartbeat^0x80),"Local data/heartbeat did not loop back");
 n.board.net_reg0=0;m2link_frame(&n.link,&n.board);
 check(n.link.state==0 && n.ram[0x8000]==0,"Disabled local board retained protocol state");
 n.board.net_reg0=1;n.board.net_reg2=0;m2link_frame(&n.link,&n.board);
 check(n.link.state==1 && !n.link.master && n.ram[0x8000]==0,"Local Slave was converted to Master");
}
}
int main() { try {
 check_local_loopback();
 for(unsigned n:{2u,3u,4u,5u,8u,9u})check_native_ring(n);
 check_netpacket_adapter();
 check(libretro::register_netpacket_interface(environment,nullptr),"Re-register");
 check_active_lobby_reconfiguration();libretro::shutdown_netpacket_interface();
 std::puts("PASS: local Master/Slave loopback; native external rings 2/3/4/5/8/9, blocks, restart/reconnect; SM2 Netpacket callbacks/rosters/queues/lobby lifecycle");return 0;
 } catch(const std::exception &e){std::fprintf(stderr,"FAIL: %s\n",e.what());return 1;}}
