#include "sharc_reset.h"
#include <string.h>
void m2_sharc_reset(m2_sharc_reset_context *c,const uint8_t *source,
    uint32_t source_token,uint32_t bytes,uint32_t fixed_state,
    const m2_sharc_program_memory *memory,const m2_sharc_registration *r)
{
    if(r && r->list) {
        m2_sharc_state_descriptor descriptor={1,fixed_state,0x2a4,0x4bc0f0,0x4bc0d0,"SHARC"};
        uint32_t head=r->read(r->opaque,r->list);
        uint32_t next=r->read(r->opaque,head+4);
        uint32_t node=r->create(r->opaque,head,next,&descriptor);
        uint32_t count=r->read(r->opaque,r->list+4);
        /* Native creates the node BEFORE checking the exact limit. Values
         * above it wrap through the unsigned subtraction and are not rejected. */
        if(count==0x0aaaaaa9u) {
            r->fatal(r->opaque,"list<T> too long");
            return; /* Unreachable under the non-returning fatal contract. */
        }
        r->write(r->opaque,r->list+4,count+1);
        r->write(r->opaque,head+4,node);
        r->write(r->opaque,r->read(r->opaque,node+4),node);
    }
    c->source_binding=source_token;c->source_next=source_token+24;
    memset(c->execution.state,0,sizeof(c->execution.state));
    c->execution.state[0x20/4]=0xffffffffu;
    c->execution.state[0xb8/4]=0xffffffffu;
    c->execution.state[8/4]=0x20018;
    m2_sharc_decode_program(source,bytes,c->selected_state,fixed_state,&c->program,memory);
    c->execution.program_base=c->program.program_base;
    c->execution.current_record=c->program.current_record;
    c->execution.stop=0;c->execution.event_count=0;c->execution.event_delay=0;
    c->execution.state[8/4]=0x20004;
    c->execution.saved_record=c->program.program_base+0xd801b0u;
}
void m2_sharc_upload_complete(m2_sharc_reset_context *c,const uint8_t *source,
    uint32_t source_token,uint32_t bytes,uint32_t fixed_state,
    const m2_sharc_program_memory *memory)
{
    m2_sharc_reset(c,source,source_token,bytes,fixed_state,memory,0);
}
