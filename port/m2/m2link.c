/* Native m2net search/register/block behavior, separated from its in-process
 * multi-board scheduler. Packet 0 counts the ring, 1 assigns native IDs, and
 * 2 exchanges the same 0xe00-byte blocks (original 0x4cf3d0/0x4cf740).
 * The transport owns delivery only. See m2net.c and EXTERNAL_LINKED_CABINETS.md. */
#include "m2link.h"
#include <string.h>
#define BLOCK 0xe00
#define AT 0x2000
#define SLOT 0x1c0
static void put16(uint8_t *p, uint16_t v) { p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8); }
void m2link_init(m2_link *l, unsigned cabinets, m2_link_transport t)
{
    memset(l,0,sizeof *l);l->cabinets=cabinets;l->transport=t;
}
void m2link_reset(m2_link *l)
{
    l->state=0;l->retry=0;l->master=0;
    if(l->transport.clear)l->transport.clear(l->transport.user);
}
static void send(m2_link *l,const uint8_t *p,size_t n)
{ l->transport.send(l->transport.user,p,n); }
static void established(m2_link *l,m2_board *b,unsigned id)
{
    uint8_t *m=b->zshared+0x8000;
    m[0]=1;m[2]=(uint8_t)id;m[3]=(uint8_t)l->cabinets;
    b->net_reg2|=0x80;l->state=3;
}
void m2link_frame(m2_link *l,m2_board *b)
{
    uint8_t *m=b->zshared+0x8000;
    if(!b->net_enabled || !(b->net_reg0&1)) {
        if(l->state)m2link_reset(l);
        m[0]=0;return;
    }
    /* Local hardware remains fitted without an external transport.
       The game's Master bit is authoritative; never turn a Slave into Master.
       No queues exist in this synchronous single-node loopback. */
    if(l->cabinets==1 && b->net_enabled==M2_NET_LOOPBACK) {
        if(!l->state) {
            b->net_reg2|=0x80;m[0]=0;put16(m+2,0xffff);
            put16(m+0x12,BLOCK);put16(m+0x14,SLOT);
            memset(m+AT,0,BLOCK);l->master=b->net_reg2&1;l->state=1;
        }
        if(l->state==1 && l->master)established(l,b,1);
        if(l->state==3) {
            uint8_t own[BLOCK];memcpy(own,m+AT,BLOCK);
            memcpy(m+AT+SLOT,own,BLOCK);b->net_reg2^=0x80;
        }
        return;
    }
    if(!l->transport.ready || !l->transport.send || !l->transport.receive
        || l->cabinets<2 || l->cabinets>9)return;
    if(!l->transport.ready(l->transport.user)) {
        if(l->state)m2link_reset(l);
        m[0]=0;put16(m+2,0xffff);return;
    }
    if(!l->state) {
        b->net_reg2|=0x80;m[0]=0;put16(m+2,0xffff);
        put16(m+0x12,BLOCK);put16(m+0x14,SLOT);
        memset(m+AT,0,BLOCK);l->master=b->net_reg2&1;l->state=1;
        /* A restarted slave requests a fresh native handshake without closing
         * its transport session or waiting for the master to restart too. */
        if(!l->master) { const uint8_t restart=3;send(l,&restart,1); }
    }
    uint8_t p[M2LINK_PACKET_MAX];size_t n;
    /* Bound processing even if a faulty transport never empties. */
    for(unsigned limit=0;limit<64 && (n=l->transport.receive(l->transport.user,p,sizeof p));limit++) {
        if(n==1 && p[0]==3) {
            l->state=1;l->retry=0;m[0]=0;put16(m+2,0xffff);
            if(!l->master)send(l,p,n);
        } else if(n==2 && p[0]==0 && p[1]>=1 && p[1]<=l->cabinets) {
            if(l->master) {
                if(p[1]!=l->cabinets)continue;
                uint8_t assign[]={1,(uint8_t)l->cabinets,2};
                send(l,assign,sizeof assign);established(l,b,1);
            } else if(p[1]<l->cabinets) { p[1]++;send(l,p,n); }
        } else if(n==3 && p[0]==1 && p[1]==l->cabinets
                  && p[2]>=2 && p[2]<=l->cabinets && !l->master) {
            established(l,b,l->cabinets-p[2]+2);
            p[2]++;send(l,p,n);
        } else if(n==BLOCK+1 && p[0]==2 && l->state==3) {
            if(!l->master) {
                uint8_t own[BLOCK+1];own[0]=2;memcpy(own+1,m+AT,BLOCK);send(l,own,sizeof own);
            }
            memcpy(m+AT+SLOT,p+1,BLOCK);b->net_reg2^=0x80;
        }
    }
    if(l->state==1 && l->master && l->retry++%6==0) {
        const uint8_t hello[]={0,1};send(l,hello,sizeof hello);
    } else if(l->state==3 && l->master) {
        p[0]=2;memcpy(p+1,m+AT,BLOCK);send(l,p,sizeof p);
    }
}
