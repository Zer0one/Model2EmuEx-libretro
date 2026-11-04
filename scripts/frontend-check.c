/* Bounded Libretro ABI/GL harness; SDL is a test-only dependency. */
#include "libretro.h"
#include <SDL2/SDL.h>
#include <SDL2/SDL_opengl.h>
#include <SDL2/SDL_opengl_glext.h>
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <zlib.h>
static struct retro_hw_render_callback *hw;
static GLuint fbo, texture;
static PFNGLBINDFRAMEBUFFERPROC bindfbo;
static FILE *pcm;
static unsigned frames, samples;
static int scale = 1;
static bool updated;
static unsigned expected_width = 496, expected_height = 384, duplicates;
static bool allow_duplicates;
static const char *aspect, *wide_mode;
static float expected_aspect = 4.0f/3.0f;
static struct retro_audio_buffer_status_callback buffer_status;
static unsigned poll_frame;
static bool play, partial_audio, mute_all;
static unsigned audio_calls;
static uint32_t state_pcm_crc;
static unsigned state_pcm_frames, nvram_resets;
static bool nvram_authority;
static const char *timing, *overlay;
static const char *filter = "nearest";
static const char *native_key, *native_value;
static PFNGLUNIFORM1FPROC real_uniform1f;
static PFNGLGETUNIFORMLOCATIONPROC uniform_location;
static unsigned mesh_modes_seen;
static bool observe_context_reset;
static unsigned reset_deletions;
static void (APIENTRY *real_delete_textures)(GLsizei,const GLuint *);
static void (APIENTRY *real_delete_buffers)(GLsizei,const GLuint *);
static void (APIENTRY *real_delete_framebuffers)(GLsizei,const GLuint *);
static void (APIENTRY *real_delete_program)(GLuint);
static void APIENTRY observe_delete_textures(GLsizei n,const GLuint *ids) {
    if(observe_context_reset)reset_deletions+=n;real_delete_textures(n,ids);
}
static void APIENTRY observe_delete_buffers(GLsizei n,const GLuint *ids) {
    if(observe_context_reset)reset_deletions+=n;real_delete_buffers(n,ids);
}
static void APIENTRY observe_delete_framebuffers(GLsizei n,const GLuint *ids) {
    if(observe_context_reset)reset_deletions+=n;real_delete_framebuffers(n,ids);
}
static void APIENTRY observe_delete_program(GLuint id) {
    if(observe_context_reset && id)reset_deletions++;real_delete_program(id);
}
static void APIENTRY observe_uniform1f(GLint location, GLfloat value)
{
    GLint program = 0;
    glGetIntegerv(GL_CURRENT_PROGRAM, &program);
    GLint mesh_location = uniform_location((GLuint)program, "meshblend");
    if (location >= 0 && location == mesh_location)
        mesh_modes_seen |= value > 0.5f ? 2u : 1u;
    real_uniform1f(location, value);
}
static uintptr_t framebuffer(void) { return fbo; }
static retro_proc_address_t proc(const char *s)
{
    void *p = SDL_GL_GetProcAddress(s); retro_proc_address_t f;
    memcpy(&f, &p, sizeof f);
    if (!strcmp(s,"glDeleteTextures")) {memcpy(&real_delete_textures,&p,sizeof real_delete_textures);f=(retro_proc_address_t)observe_delete_textures;}
    if (!strcmp(s,"glDeleteBuffers")) {memcpy(&real_delete_buffers,&p,sizeof real_delete_buffers);f=(retro_proc_address_t)observe_delete_buffers;}
    if (!strcmp(s,"glDeleteFramebuffers")) {memcpy(&real_delete_framebuffers,&p,sizeof real_delete_framebuffers);f=(retro_proc_address_t)observe_delete_framebuffers;}
    if (!strcmp(s,"glDeleteProgram")) {memcpy(&real_delete_program,&p,sizeof real_delete_program);f=(retro_proc_address_t)observe_delete_program;}
    if (!strcmp(s, "glUniform1f")) {
        memcpy(&real_uniform1f, &p, sizeof real_uniform1f);
        void *q = SDL_GL_GetProcAddress("glGetUniformLocation");
        memcpy(&uniform_location, &q, sizeof uniform_location);
        f = (retro_proc_address_t)observe_uniform1f;
    }
    return f;
}
static bool environment(unsigned cmd, void *data)
{
    switch (cmd) {
    case RETRO_ENVIRONMENT_SET_MESSAGE:
        if(strstr(((struct retro_message *)data)->msg,"NVRAM Settings Applied"))nvram_resets++;
        return true;
    case RETRO_ENVIRONMENT_GET_SYSTEM_DIRECTORY:
        *(const char **)data=getenv("CHECK_SYSTEM");return *(const char **)data!=NULL;
    case RETRO_ENVIRONMENT_GET_CORE_OPTIONS_VERSION: *(unsigned *)data = 2; return true;
    case RETRO_ENVIRONMENT_SET_CORE_OPTIONS_V2: {
        struct retro_core_options_v2 *o = data;
        const struct retro_core_option_v2_definition *filter_def = NULL;
        unsigned count = 0;
        for (;o->definitions[count].key;count++) {
            const struct retro_core_option_v2_definition *d = &o->definitions[count];
            if (!strcmp(d->key, "model2emuex_texture_filter")) filter_def = d;
        }
        assert(count > 14); /* native controls plus the complete reference NVRAM catalogue */
        assert(filter_def && !strcmp(filter_def->default_value, "nearest"));
        return true;
    }
    case RETRO_ENVIRONMENT_SET_HW_RENDER:
        hw = data; assert(hw->context_type == RETRO_HW_CONTEXT_OPENGL);
        hw->get_current_framebuffer = framebuffer; hw->get_proc_address = proc; return true;
    case RETRO_ENVIRONMENT_SET_GEOMETRY: {
        struct retro_game_geometry *g = data;
        expected_width = g->base_width; expected_height = g->base_height; expected_aspect = g->aspect_ratio; return true;
    }
    case RETRO_ENVIRONMENT_SET_AUDIO_BUFFER_STATUS_CALLBACK:
        buffer_status = *(struct retro_audio_buffer_status_callback *)data; return true;
    case RETRO_ENVIRONMENT_SET_PIXEL_FORMAT: return *(enum retro_pixel_format *)data == RETRO_PIXEL_FORMAT_XRGB8888;
    case RETRO_ENVIRONMENT_GET_VARIABLE: {
        struct retro_variable *v = data;
        if(getenv("CHECK_MANX_CABINET")) {
            if(!strcmp(v->key,"model2emuex_nvram_settings")) { v->value="enabled";return true; }
            if(!strcmp(v->key,"model2emuex_nvram_manxtt_cabinet_type")) { v->value=getenv("CHECK_MANX_CABINET");return true; }
        }
        if(getenv("CHECK_NETWORK_ROLE") && !strncmp(v->key,"model2emuex_automatic_network_",29)) {
            v->value=getenv("CHECK_NETWORK_ROLE");return true;
        }
        if(nvram_authority && !strcmp(v->key,"model2emuex_nvram_settings")) {v->value="enabled";return true;}
        if(nvram_authority && !strcmp(v->key,"model2emuex_nvram_vf2_difficulty")) {v->value="hard";return true;}
        if (mute_all && (!strcmp(v->key,"model2emuex_scsp_gain") || !strcmp(v->key,"model2emuex_multipcm1_gain") || !strcmp(v->key,"model2emuex_multipcm2_gain") || !strcmp(v->key,"model2emuex_ym3438_gain"))) { v->value="0"; return true; }
        if (overlay && !strcmp(v->key,"model2emuex_timing_overlay")) {v->value=overlay;return true;}
        if (timing && !strcmp(v->key, "model2emuex_av_timing")) { v->value = timing; return true; }
        if (aspect && !strcmp(v->key, "model2emuex_aspect_ratio")) { v->value = aspect; return true; }
        if (wide_mode && !strcmp(v->key, "model2emuex_widescreen_mode")) { v->value = wide_mode; return true; }
        if (native_key && !strcmp(v->key, native_key)) { v->value = native_value; return true; }
        if (!strcmp(v->key, "model2emuex_texture_filter")) { v->value = filter; return true; }
        if (!strcmp(v->key, "model2emuex_internal_resolution")) { static char selected_scale[2];selected_scale[0]=(char)('0'+scale);selected_scale[1]=0;v->value=selected_scale; return true; }
        v->value = NULL; return false;
    }
    case RETRO_ENVIRONMENT_GET_VARIABLE_UPDATE: *(bool *)data = updated; updated = false; return true;
    case RETRO_ENVIRONMENT_SET_INPUT_DESCRIPTORS:
    case RETRO_ENVIRONMENT_SET_SUPPORT_NO_GAME: return true;
    default: return false;
    }
}
static void video(const void *data, unsigned w, unsigned h, size_t pitch)
{
    (void)pitch;
    assert(data == RETRO_HW_FRAME_BUFFER_VALID || (allow_duplicates && data == NULL));
    if (!data) duplicates++;
    assert(w == expected_width && h == expected_height);
    assert(glGetError() == GL_NO_ERROR);
    frames++;
}
static size_t audio(const int16_t *data, size_t n)
{
    if (partial_audio && ++audio_calls % 7 == 0) return 0;
    state_pcm_crc=(uint32_t)crc32(state_pcm_crc,(const uint8_t *)data,(uInt)(n*4));state_pcm_frames+=(unsigned)n;
    if (pcm) assert(fwrite(data, 4, n, pcm) == n);
    samples += n; return n;
}
static void poll(void) { poll_frame++; }
static int16_t input(unsigned port, unsigned device, unsigned index, unsigned id)
{
    (void)index;
    assert(device != RETRO_DEVICE_KEYBOARD); /* Frontend owns keyboard mapping. */
    if (!play || port || device != RETRO_DEVICE_JOYPAD) return 0;
    if (id == RETRO_DEVICE_ID_JOYPAD_SELECT)
        return (poll_frame >= 950 && poll_frame < 960) || (poll_frame >= 1000 && poll_frame < 1010);
    if (id == RETRO_DEVICE_ID_JOYPAD_START) return poll_frame >= 1100 && poll_frame < 1110;
    if (id == RETRO_DEVICE_ID_JOYPAD_A) return poll_frame >= 1300 && poll_frame % 30 < 5;
    return 0;
}
static void dump(const char *dir, const char *name, const void *data, size_t size)
{
    char path[4096]; snprintf(path, sizeof path, "%s/%s", dir, name);
    FILE *f = fopen(path, "wb"); assert(f); assert(fwrite(data, 1, size, f) == size); fclose(f);
}
#define LOAD(name) __typeof__(&name) p_##name = dlsym(lib, #name); assert(p_##name)
int main(int argc, char **argv)
{
    if (argc != 5) { fprintf(stderr, "usage: frontend-check core.dylib game.zip frames output-dir\n"); return 2; }
    play = getenv("CHECK_PLAY") != NULL;
    partial_audio = getenv("CHECK_AUDIO_PARTIAL") != NULL;
    mute_all = getenv("CHECK_MUTE_ALL") != NULL;
    timing = getenv("CHECK_TIMING");
    overlay = getenv("CHECK_OVERLAY");
    if (getenv("CHECK_FILTER")) filter = getenv("CHECK_FILTER");
    native_key = getenv("CHECK_OPTION_KEY"); native_value = getenv("CHECK_OPTION_VALUE");
    void *lib = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL); if (!lib) { puts(dlerror()); return 1; }
    LOAD(retro_set_environment); LOAD(retro_set_video_refresh); LOAD(retro_set_audio_sample_batch);
    LOAD(retro_set_input_poll); LOAD(retro_set_input_state); LOAD(retro_init); LOAD(retro_load_game);
    LOAD(retro_run); LOAD(retro_unload_game); LOAD(retro_deinit); LOAD(retro_get_memory_data);
    LOAD(retro_get_memory_size); LOAD(retro_reset); LOAD(retro_get_system_av_info);
    LOAD(retro_serialize_size); LOAD(retro_serialize); LOAD(retro_unserialize);
    p_retro_set_environment(environment); p_retro_set_video_refresh(video);
    p_retro_set_audio_sample_batch(audio); p_retro_set_input_poll(poll); p_retro_set_input_state(input); p_retro_init();
    struct retro_game_info game = {.path=argv[2]};
    assert(p_retro_load_game(&game));
    if(getenv("CHECK_STATE_UNAVAILABLE")) {
        unsigned char probe[128],before[128];memset(probe,0xa5,sizeof probe);
        memcpy(before,probe,sizeof probe);
        assert(p_retro_serialize_size()==0);
        assert(!p_retro_serialize(probe,sizeof probe));
        assert(!p_retro_unserialize(probe,sizeof probe));
        assert(!memcmp(probe,before,sizeof probe));
    }
    struct retro_system_av_info av;
    p_retro_get_system_av_info(&av);
    double loaded_fps = timing && !strcmp(timing, "native") ? 58.0 : 60.0;
    assert(av.timing.fps == loaded_fps && av.timing.sample_rate == 44100.0);
    dump(argv[4], "core.initial-nvram", p_retro_get_memory_data(RETRO_MEMORY_SAVE_RAM), p_retro_get_memory_size(RETRO_MEMORY_SAVE_RAM));
    assert(SDL_Init(SDL_INIT_VIDEO) == 0);
    SDL_GL_SetAttribute(SDL_GL_CONTEXT_MAJOR_VERSION, 2); SDL_GL_SetAttribute(SDL_GL_CONTEXT_MINOR_VERSION, 1);
    SDL_Window *win = SDL_CreateWindow("Model2EmuEx Libretro Check", 0, 0, 496, 384, SDL_WINDOW_OPENGL | SDL_WINDOW_HIDDEN);
    assert(win); SDL_GLContext ctx = SDL_GL_CreateContext(win); assert(ctx);
    PFNGLGENFRAMEBUFFERSPROC genfbo = (PFNGLGENFRAMEBUFFERSPROC)SDL_GL_GetProcAddress("glGenFramebuffers");
    bindfbo = (PFNGLBINDFRAMEBUFFERPROC)SDL_GL_GetProcAddress("glBindFramebuffer");
    PFNGLFRAMEBUFFERTEXTURE2DPROC attach = (PFNGLFRAMEBUFFERTEXTURE2DPROC)SDL_GL_GetProcAddress("glFramebufferTexture2D");
    PFNGLDELETEFRAMEBUFFERSPROC delfbo = (PFNGLDELETEFRAMEBUFFERSPROC)SDL_GL_GetProcAddress("glDeleteFramebuffers");
    genfbo(1, &fbo); assert(fbo); bindfbo(GL_FRAMEBUFFER, fbo);
    glGenTextures(1, &texture); glBindTexture(GL_TEXTURE_2D, texture);
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, 1984, 1536, 0, GL_RGBA, GL_UNSIGNED_BYTE, NULL);
    attach(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, texture, 0);
    hw->context_reset();
    char path[4096]; snprintf(path, sizeof path, "%s/core.pcm", argv[4]); pcm = fopen(path, "wb"); assert(pcm);
    if(getenv("CHECK_STATE_COLD")) {
        size_t capacity=p_retro_serialize_size();void *cold=malloc(capacity);assert(cold);
        assert(p_retro_serialize(cold,capacity));assert(p_retro_unserialize(cold,capacity));free(cold);
    }
    const char *external_state=getenv("CHECK_LOAD_STATE");
    if(external_state) {
        size_t capacity=p_retro_serialize_size();void *bytes=malloc(capacity);assert(bytes);
        FILE *saved=fopen(external_state,"rb");assert(saved);assert(fread(bytes,1,capacity,saved)==capacity);fclose(saved);
        assert(p_retro_unserialize(bytes,capacity));free(bytes);
        if(getenv("CHECK_LOAD_INPUT_FRAME"))poll_frame=(unsigned)atoi(getenv("CHECK_LOAD_INPUT_FRAME"));
    }
    for (int i = 0; i < atoi(argv[3]); i++) p_retro_run();
    fclose(pcm); pcm = NULL;
    if (!external_state && (!partial_audio || atoi(argv[3]) % 7 != 0))
        assert(samples == (unsigned)(atoi(argv[3]) * 44100.0 / loaded_fps));
    printf("Timing: %.0f Hz, %u PCM frames for %s machine frames\n", loaded_fps, samples, argv[3]);
    if (atoi(argv[3]) >= 1800) {
        unsigned expected = native_key && !strcmp(native_key, "model2emuex_mesh") &&
            native_value && !strcmp(native_value, "checker") ? 1u : 2u;
        assert(mesh_modes_seen & expected);
    }
    dump(argv[4], "core.ram", p_retro_get_memory_data(RETRO_MEMORY_SYSTEM_RAM), p_retro_get_memory_size(RETRO_MEMORY_SYSTEM_RAM));
    dump(argv[4], "core.nvram", p_retro_get_memory_data(RETRO_MEMORY_SAVE_RAM), p_retro_get_memory_size(RETRO_MEMORY_SAVE_RAM));
    unsigned char *rgb = malloc(496 * 384 * 3); assert(rgb);
    bindfbo(GL_FRAMEBUFFER, fbo); glPixelStorei(GL_PACK_ALIGNMENT, 1);
    glReadPixels(0, 0, 496, 384, GL_RGB, GL_UNSIGNED_BYTE, rgb);
    snprintf(path, sizeof path, "%s/core.ppm", argv[4]); FILE *shot = fopen(path, "wb"); assert(shot);
    fprintf(shot, "P6\n496 384\n255\n");
    for (int y = 383; y >= 0; y--) fwrite(rgb + y * 496 * 3, 3, 496, shot);
    fclose(shot); free(rgb);
    if(getenv("CHECK_STATE")) {
        size_t capacity=p_retro_serialize_size();
        assert(capacity==((getenv("CHECK_SHARC_STATE") || getenv("CHECK_TGPX4_STATE"))?16u:12u)*1024u*1024u);
        uint8_t *saved=malloc(capacity),*expected=malloc(capacity),*actual=malloc(capacity),*bad=malloc(capacity);
        uint8_t *image=malloc(496*384*3);assert(saved && expected && actual && bad && image);
        assert(!p_retro_serialize(NULL,capacity));assert(!p_retro_serialize(saved,capacity-1));
        assert(p_retro_serialize(saved,capacity));dump(argv[4],"core.state",saved,capacity);
        unsigned input_at_save=poll_frame;
        state_pcm_crc=0;state_pcm_frames=0;
        for(unsigned step=0;step<12;step++)p_retro_run();
        uint32_t pcm_expected=state_pcm_crc;unsigned pcm_frames_expected=state_pcm_frames;
        assert(p_retro_serialize(expected,capacity));
        bindfbo(GL_FRAMEBUFFER,fbo);glReadPixels(0,0,496,384,GL_RGB,GL_UNSIGNED_BYTE,image);
        dump(argv[4],"continued.rgb",image,496*384*3);
        for(unsigned repeat=0;repeat<4;repeat++) {
            assert(p_retro_unserialize(saved,capacity));poll_frame=input_at_save;
            state_pcm_crc=0;state_pcm_frames=0;
            for(unsigned step=0;step<12;step++)p_retro_run();
            assert(state_pcm_crc==pcm_expected && state_pcm_frames==pcm_frames_expected);
            assert(p_retro_serialize(actual,capacity));
            if(memcmp(expected,actual,capacity)) {
                dump(argv[4],"expected.state",expected,capacity);dump(argv[4],"actual.state",actual,capacity);
                for(size_t i=0;i<capacity;i++)if(expected[i]!=actual[i]) {fprintf(stderr,"State mismatch offset %zu: %02x %02x\n",i,expected[i],actual[i]);if(i>200)break;}
                assert(!"Restored continuation state differs");
            }
            unsigned char *second=malloc(496*384*3);assert(second);
            bindfbo(GL_FRAMEBUFFER,fbo);glReadPixels(0,0,496,384,GL_RGB,GL_UNSIGNED_BYTE,second);
            dump(argv[4],"restored.rgb",second,496*384*3);assert(!memcmp(image,second,496*384*3));free(second);
        }
        assert(!p_retro_unserialize(NULL,capacity));assert(!p_retro_unserialize(saved,capacity-1));
        const size_t damaged_offsets[]={0,8,12,16,20,24,28,32,64,96,100,108,112,113,114,127,128,capacity/2,capacity-1};
        for(unsigned n=0;n<sizeof damaged_offsets/sizeof damaged_offsets[0];n++) {
            memcpy(bad,saved,capacity);bad[damaged_offsets[n]]^=0xff;
            /* Recompute integrity for semantic header rejection cases. */
            if(damaged_offsets[n]<128 && damaged_offsets[n]!=16) {
                uint32_t crc=(uint32_t)crc32(0,bad,16);crc=(uint32_t)crc32(crc,bad+20,(uInt)(capacity-20));memcpy(bad+16,&crc,4);
            }
            assert(!p_retro_unserialize(bad,capacity));
            assert(p_retro_serialize(actual,capacity));assert(!memcmp(expected,actual,capacity));
        }
        memcpy(bad,saved,capacity);
        const size_t memories=0x100000+0x80000+0x40000+0x10000+0x100000+0x10000+0x18000+0x10004+0x20004+0x80000+0x40000+0x40000+0x20000+0x100004+0x100004+0x18000+0x10000;
        const size_t fc_index=128+memories+4+32*4+4+4*8+6*4+4*4+1+4;
        memset(bad+fc_index,0xff,4);
        uint32_t checksum=(uint32_t)crc32(0,bad,16);checksum=(uint32_t)crc32(checksum,bad+20,(uInt)(capacity-20));memcpy(bad+16,&checksum,4);
        assert(!p_retro_unserialize(bad,capacity));assert(p_retro_serialize(actual,capacity));assert(!memcmp(expected,actual,capacity));
        /* Restore snapshots in reverse order as rewind does. */
        assert(p_retro_unserialize(expected,capacity));assert(p_retro_serialize(actual,capacity));assert(!memcmp(expected,actual,capacity));
        assert(p_retro_unserialize(saved,capacity));poll_frame=input_at_save;
        hw->context_destroy();hw->context_reset();
        for(unsigned n=0;n<12;n++)p_retro_run();
        assert(p_retro_serialize(actual,capacity));assert(!memcmp(expected,actual,capacity));
        dump(argv[4],"continued.state",expected,capacity);
        if(strstr(argv[2],"/vf2.zip")) {
            nvram_authority=true;unsigned resets=nvram_resets;updated=true;
            assert(p_retro_unserialize(saved,capacity));p_retro_run();
            const uint8_t *nv=p_retro_get_memory_data(RETRO_MEMORY_SAVE_RAM);
            assert((nv[13122]&3)==2 && nvram_resets==resets+1);
            p_retro_run();assert(nvram_resets==resets+1);
            assert(p_retro_unserialize(saved,capacity));p_retro_run();assert(nvram_resets==resets+2);
            nvram_authority=false;updated=true;assert(p_retro_unserialize(saved,capacity));p_retro_run();
            assert((nv[13122]&3)==1 && nvram_resets==resets+2);
            printf("PASS Save States NVRAM: enabled current overrides win with one reset; disabled preserves restored choices\n");
        }
        printf("PASS Save States: %zu bytes; 4 exact 12-frame RAM/device/PCM/image continuations; invalid/truncated/corrupt/identity/version rejection without mutation; PCM CRC %08x (%u frames)\n",capacity,pcm_expected,pcm_frames_expected);
        free(saved);free(expected);free(actual);free(bad);free(image);
        hw->context_destroy();p_retro_unload_game();p_retro_deinit();
        delfbo(1,&fbo);glDeleteTextures(1,&texture);SDL_GL_DeleteContext(ctx);SDL_DestroyWindow(win);SDL_Quit();dlclose(lib);
        return 0;
    }
    /* Native filter changes must apply without advancing/resetting content
     * outside the normal run loop or causing GL errors. */
    filter = "bilinear"; updated = true; p_retro_run();
    filter = "trilinear"; updated = true; p_retro_run();
    filter = "invalid"; updated = true; p_retro_run(); /* nearest fallback */
    filter = "nearest"; updated = true; p_retro_run();
    native_key = "model2emuex_gamma_r"; native_value = "1.50"; updated = true; p_retro_run();
    native_value = "nan"; updated = true; p_retro_run();
    native_key = "model2emuex_saturation"; native_value = "1.50"; updated = true; p_retro_run();
    native_key = "model2emuex_mesh"; native_value = "checker"; updated = true; p_retro_run();
    native_key = NULL; native_value = NULL; updated = true; p_retro_run();
    /* Display stretching and 3D expansion are independent, matching SM2. */
    aspect = "16_9"; wide_mode = "stretch"; updated = true; p_retro_run();
    assert(expected_width == 496 && expected_aspect > 1.77f);
    wide_mode = "expand_3d"; updated = true; p_retro_run();
    assert(expected_width == 662 && expected_height == 384);
    aspect = "16_10"; updated = true; p_retro_run(); assert(expected_width == 596);
    aspect = "4_3"; updated = true; p_retro_run(); assert(expected_width == 496 && expected_aspect < 1.34f);
    aspect = "auto"; updated = true; p_retro_run(); assert(expected_width == 662);
    wide_mode = "stretch"; updated = true; p_retro_run(); assert(expected_width == 496 && expected_aspect < 1.34f);
    aspect = "16_10"; updated = true; p_retro_run(); assert(expected_width == 496 && expected_aspect == 1.6f);
    aspect = "invalid"; wide_mode = "invalid"; updated = true; p_retro_run();
    assert(expected_width == 496 && expected_aspect < 1.34f);
    aspect = NULL; wide_mode = NULL;
    native_key = "model2emuex_pipeline"; native_value = "disabled"; updated = true; p_retro_run();
    native_key = NULL; native_value = NULL; updated = true; p_retro_run();
    assert(buffer_status.callback);
    allow_duplicates = true;
    unsigned before_skip = duplicates;
    buffer_status.callback(true, 10, true);
    p_retro_run(); p_retro_run(); p_retro_run();
    assert(duplicates - before_skip == 2);
    buffer_status.callback(true, 80, false);
    allow_duplicates = false;
    /* Resolution updates and graphics-resource recreation. */
    scale = 2; updated = true; p_retro_run();
    hw->context_destroy(); hw->context_reset(); p_retro_run();
    if (getenv("CHECK_CONTEXT_LOSS")) {
        /* Replacement context, deliberately without the old destroy callback.
         * The old renderer/overlays must forget names, not delete new objects. */
        SDL_GLContext replacement=SDL_GL_CreateContext(win);assert(replacement);
        genfbo(1,&fbo);bindfbo(GL_FRAMEBUFFER,fbo);
        glGenTextures(1,&texture);glBindTexture(GL_TEXTURE_2D,texture);
        glTexImage2D(GL_TEXTURE_2D,0,GL_RGBA,1984,1536,0,GL_RGBA,GL_UNSIGNED_BYTE,NULL);
        attach(GL_FRAMEBUFFER,GL_COLOR_ATTACHMENT0,GL_TEXTURE_2D,texture,0);
        reset_deletions=0;observe_context_reset=true;
        hw->context_reset();observe_context_reset=false;
        assert(reset_deletions==0);
        p_retro_run();
        bindfbo(GL_FRAMEBUFFER,fbo);
        size_t pixels=(size_t)expected_width*expected_height;
        unsigned char *image=malloc(pixels*4);assert(image);
        glReadPixels(0,0,expected_width,expected_height,GL_RGBA,GL_UNSIGNED_BYTE,image);
        bool visible=false;
        for(size_t i=0;i<pixels;i++)visible|=(image[4*i]|image[4*i+1]|image[4*i+2])!=0;
        free(image);assert(visible);
        SDL_GL_DeleteContext(ctx);ctx=replacement;
        fprintf(stderr,"Unannounced replacement context: no stale GL deletes; rendering resumed\n");
    }
    if (getenv("CHECK_OVERLAY_TEST")) {
        const char *modes[]={"disabled","auto","11","12","13","14","invalid"};
        for(unsigned mode=0;mode<sizeof modes/sizeof modes[0];++mode) {
            overlay=modes[mode];updated=true;
            for(unsigned n=0;n<64;++n)p_retro_run();
        }
        overlay="14";scale=4;updated=true;
        for(unsigned n=0;n<64;++n)p_retro_run();
        bindfbo(GL_FRAMEBUFFER,fbo);
        unsigned char *large=malloc(1984u*1536u*3u);assert(large);
        glReadPixels(0,0,1984,1536,GL_RGB,GL_UNSIGNED_BYTE,large);
        snprintf(path,sizeof path,"%s/overlay-4x.ppm",argv[4]);FILE *f=fopen(path,"wb");assert(f);
        fprintf(f,"P6\n1984 1536\n255\n");
        for(int y=1535;y>=0;--y)fwrite(large+(size_t)y*1984*3,3,1984,f);
        fclose(f);free(large);
        hw->context_destroy();hw->context_reset();
        for(unsigned n=0;n<64;++n)p_retro_run();
        scale=1;updated=true;p_retro_run();
    }
    /* The restart-required timing choice is latched until unload/reload. */
    timing = loaded_fps == 58.0 ? "60hz" : "native";
    updated = true; p_retro_run();
    p_retro_get_system_av_info(&av); assert(av.timing.fps == loaded_fps);
    /* Save RAM remains valid across reset. */
    uint8_t *nv = p_retro_get_memory_data(RETRO_MEMORY_SAVE_RAM);
    uint8_t before[0x10080]; memcpy(before, nv, sizeof before);
    p_retro_reset(); assert(!memcmp(before, nv, sizeof before)); p_retro_run();
    p_retro_get_system_av_info(&av); assert(av.timing.fps == loaded_fps);
    hw->context_destroy(); p_retro_unload_game();
    /* Reload must import frontend SRAM before executing its first frame. */
    assert(p_retro_load_game(&game));
    p_retro_get_system_av_info(&av); assert(av.timing.fps == (loaded_fps == 58.0 ? 60.0 : 58.0));
    nv = p_retro_get_memory_data(RETRO_MEMORY_SAVE_RAM); nv[0xff00] = 0xa7;
    hw->context_reset(); p_retro_run(); assert(nv[0xff00] == 0xa7);
    hw->context_destroy(); p_retro_unload_game(); p_retro_deinit();
    delfbo(1, &fbo); glDeleteTextures(1, &texture);
    SDL_GL_DeleteContext(ctx); SDL_DestroyWindow(win); SDL_Quit(); dlclose(lib);
    printf("PASS: %u video callbacks, %u audio frames; nonzero frontend FBO, native image/widescreen/pipeline updates, bounded frame skip, 2x update, context reset, machine reset, SRAM import, unload/reload\n", frames, samples);
    return 0;
}
