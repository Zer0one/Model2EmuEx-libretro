#include "sm2_timing.h"
#include <cassert>
#include <cmath>
#include <iostream>
static bool near(float a,float b) {return std::abs(a-b)<0.02f;}
int main() {
    sm2lr_timing_config(13,false,60);
    for(unsigned i=0;i<60;++i)sm2lr_timing_sample(10,5,2,12,1000+i*1000.0/60);
    assert(!sm2lr_timing_data().valid);
    sm2lr_timing_sample(10,5,2,15,2000);
    auto d=sm2lr_timing_data();
    assert(d.enabled && d.valid && d.font_pixels==13 && !d.native_timing);
    assert(near(d.machine_ms,10) && near(d.video_ms,5) && near(d.audio_ms,2));
    assert(near(d.run_ms,12+3.0f/61) && near(d.worst_ms,15) && near(d.actual_fps,60));
    assert(near(d.engine_cap_fps,1000.0f/15) && near(d.callback_cap_fps,1000.0f/(12+3.0f/61)));
    sm2lr_timing_config(11,false,60);assert(sm2lr_timing_data().valid && sm2lr_timing_data().font_pixels==11);
    sm2lr_timing_config(0,false,60);assert(!sm2lr_timing_data().enabled && !sm2lr_timing_data().valid);
    for(unsigned i=0;i<62;++i)sm2lr_timing_sample(100,100,100,100,3000+i*20);
    assert(!sm2lr_timing_data().valid);
    sm2lr_timing_config(14,true,58);
    for(unsigned i=0;i<61;++i)sm2lr_timing_sample(1,2,3,4,10000+i*1000.0/58);
    d=sm2lr_timing_data();assert(d.native_timing && near(d.actual_fps,58) && near(d.worst_ms,4));
    sm2lr_timing_clear();assert(d.valid && !sm2lr_timing_data().valid);
    sm2lr_timing_shutdown();
    std::cout<<"PASS: 61-frame timing window, cadence/means/max/capacity, Off, font change and reset lifecycle\n";
}
