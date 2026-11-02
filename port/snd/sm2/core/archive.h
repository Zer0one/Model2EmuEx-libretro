// Value-only adapter for the unchanged SM2 I8251 serializer.
#pragma once
#include "../../../state.h"
#include <type_traits>
namespace sm2 {
class Archive {
    m2_state *state;
    unsigned field=0,byte_cycles=0;
public:
    explicit Archive(m2_state *a):state(a){}
    template<class T> void raw(T &value) {
        if constexpr(std::is_same_v<T,bool>) {
            uint8_t b=value?1:0;m2_state_value(state,&b,sizeof b);
            if(b>1)state->failed=1;else value=b!=0;
        } else {
            m2_state_value(state,&value,sizeof value);
            if constexpr(sizeof(T)==4) {
                if(field==0) { byte_cycles=value;if(!value || value>10000000)state->failed=1; }
                else if(value>byte_cycles)state->failed=1;
            }
        }
        ++field;
    }
};
}
