/* ROM-free checks through the production adapter and shared gun profiles. */
#include "../src/libretro/libretro.c"
#include <assert.h>
static int16_t view_x;
static bool view_environment(unsigned command,void *data)
{
    if(command!=RETRO_ENVIRONMENT_GET_VARIABLE)return false;
    struct retro_variable *v=data;
    v->value=!strcmp(v->key,"model2emuex_gun_input")?"lightgun":NULL;
    return v->value!=NULL;
}
static int16_t view_input(unsigned port,unsigned device,unsigned index,unsigned id)
{
    (void)port;(void)index;
    return device==RETRO_DEVICE_LIGHTGUN && id==RETRO_DEVICE_ID_LIGHTGUN_SCREEN_X?view_x:0;
}
static void check_view(unsigned columns)
{
    for(unsigned endpoint=0;endpoint<2;++endpoint) {
        view_x=endpoint?32767:-32768;
        read_input();
        for(unsigned player=0;player<2;++player) {
            unsigned minimum=player?0x86:0x89, maximum=player?0x273:0x276;
            unsigned extra=((maximum-minimum)*columns+248)/496;
            unsigned expected=endpoint?maximum+extra-1:minimum-extra+1;
            uint32_t raw=board->gun_xy[player*2];
            unsigned actual=((raw-0x53)&255)|(((raw+0xad)>>8)<<8);
            assert(actual==expected);
            assert(board->gun_word==3 && (board->port[1]&3)==3);
        }
    }
}
int main(int argc,char **argv)
{
    assert(argc==2);
    m2_board fixture={0};fixture.game=m2_find_game("vcop2");assert(fixture.game);fixture.type=1;
    board=&fixture;env=view_environment;input=view_input;poll_input=NULL;
    sm2lr_input_environment(env);sm2_profile=sm2lr_input_bind(board);assert(sm2_profile);
    aspect_ratio=1;expand_3d=false;check_view(0);
    aspect_ratio=2;expand_3d=true;assert(render_width()==662);check_view(83);
    resolution=4;check_view(83);
    aspect_ratio=3;assert(render_width()==596);check_view(50);
    expand_3d=false;check_view(0);
    expand_3d=true;aspect_ratio=2;
    m2lr_lua_open(board,argv[1],"vcop2",NULL);assert(m2lr_lua_active());
    check_view(0);
    m2lr_lua_event("Frame");check_view(83);
    sm2lr_input_reset();check_view(83);
    sm2lr_input_after_state_load();check_view(83);
    m2lr_lua_event("Frame");check_view(0);
    /* PostDraw can change the next scene after a wide image was submitted.
     * Input still aims at that image until the next image is presented. */
    presented_columns=83;check_view(83);
    m2lr_lua_event("PostDraw");check_view(83);
    m2lr_lua_event("PostDraw");check_view(83);
    presented_columns=0;check_view(0);
    presented_columns=-1;check_view(0);
    m2lr_lua_close();check_view(83);
    sm2lr_input_clear();board=NULL;
    puts("PASS: native width, 4:3/16:9/16:10, resolution independence, P1/P2 endpoints, Lua scene changes, reset and input Load State recovery");
    return 0;
}
