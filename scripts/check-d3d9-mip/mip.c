/* Reproduce the sampler call in ElSemi 1.1a and measure actual LOD.
 * Explicitly coloured mip levels distinguish point, blended and disabled LOD.
 * The generated-chain control uses ElSemi's A8R8G8B8 grayscale upload. */
#define COBJMACROS
#include <d3d9.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>

#define CHECK(call) do { HRESULT hr_ = (call); if (FAILED(hr_)) { \
    fprintf(stderr, "%s: %08lx\n", #call, (unsigned long)hr_); exit(1); } } while (0)

struct vertex {float x,y,z,rhw,u,v;};

static uint32_t sample(IDirect3DDevice9 *dev, IDirect3DSurface9 *target,
                       IDirect3DSurface9 *readback, float tiles)
{
    struct vertex v[] = {{-.5f,-.5f,.5f,1,0,0},{15.5f,-.5f,.5f,1,tiles,0},
                         {-.5f,15.5f,.5f,1,0,tiles},{15.5f,15.5f,.5f,1,tiles,tiles}};
    CHECK(IDirect3DDevice9_Clear(dev,0,NULL,D3DCLEAR_TARGET,0xffff00ff,1,0));
    CHECK(IDirect3DDevice9_BeginScene(dev));
    CHECK(IDirect3DDevice9_DrawPrimitiveUP(dev,D3DPT_TRIANGLESTRIP,2,v,sizeof v[0]));
    CHECK(IDirect3DDevice9_EndScene(dev));
    CHECK(IDirect3DDevice9_GetRenderTargetData(dev,target,readback));
    D3DLOCKED_RECT r;
    CHECK(IDirect3DSurface9_LockRect(readback,&r,NULL,D3DLOCK_READONLY));
    uint32_t pixel = ((uint32_t *)((char *)r.pBits + 6*r.Pitch))[6];
    CHECK(IDirect3DSurface9_UnlockRect(readback));
    return pixel & 0xffffff;
}

int main(void)
{
    HWND win = CreateWindowA("STATIC","M2 D3D9 sampler",WS_OVERLAPPEDWINDOW,
                              0,0,80,80,NULL,NULL,GetModuleHandle(NULL),NULL);
    IDirect3D9 *d3d = Direct3DCreate9(D3D_SDK_VERSION);
    if (!win || !d3d) return 1;
    D3DADAPTER_IDENTIFIER9 id;
    CHECK(IDirect3D9_GetAdapterIdentifier(d3d,0,0,&id));
    printf("adapter=%s driver=%s version=%08lx:%08lx\n",id.Description,id.Driver,
           (unsigned long)id.DriverVersion.HighPart,(unsigned long)id.DriverVersion.LowPart);
    D3DPRESENT_PARAMETERS pp = {0};
    pp.Windowed = TRUE; pp.hDeviceWindow = win; pp.SwapEffect = D3DSWAPEFFECT_DISCARD;
    IDirect3DDevice9 *dev;
    CHECK(IDirect3D9_CreateDevice(d3d,0,D3DDEVTYPE_HAL,win,D3DCREATE_SOFTWARE_VERTEXPROCESSING,&pp,&dev));
    IDirect3DSurface9 *target, *readback;
    CHECK(IDirect3DDevice9_CreateRenderTarget(dev,16,16,D3DFMT_A8R8G8B8,D3DMULTISAMPLE_NONE,0,FALSE,&target,NULL));
    CHECK(IDirect3DDevice9_CreateOffscreenPlainSurface(dev,16,16,D3DFMT_A8R8G8B8,D3DPOOL_SYSTEMMEM,&readback,NULL));
    CHECK(IDirect3DDevice9_SetRenderTarget(dev,0,target));
    CHECK(IDirect3DDevice9_SetFVF(dev,D3DFVF_XYZRHW|D3DFVF_TEX1));
    CHECK(IDirect3DDevice9_SetRenderState(dev,D3DRS_CULLMODE,D3DCULL_NONE));
    CHECK(IDirect3DDevice9_SetTextureStageState(dev,0,D3DTSS_COLOROP,D3DTOP_SELECTARG1));
    CHECK(IDirect3DDevice9_SetTextureStageState(dev,0,D3DTSS_COLORARG1,D3DTA_TEXTURE));
    for (int autogen=0;autogen<2;++autogen) {
        IDirect3DTexture9 *tex;
        CHECK(IDirect3DDevice9_CreateTexture(dev,64,64,0,autogen?D3DUSAGE_AUTOGENMIPMAP:0,
                                             D3DFMT_A8R8G8B8,D3DPOOL_MANAGED,&tex,NULL));
        UINT levels=IDirect3DTexture9_GetLevelCount(tex);
        for (UINT i=0;i<levels;++i) {
            D3DLOCKED_RECT r;
            CHECK(IDirect3DTexture9_LockRect(tex,i,&r,NULL,0));
            for (unsigned y=0;y<(64u>>i);++y) for(unsigned x=0;x<(64u>>i);++x)
                ((uint32_t*)((char*)r.pBits+y*r.Pitch))[x]=0xff000000u |
                    (autogen ? (((x^y)&1)?0xf0f0f0u:0) : (i*32u*0x010101u));
            CHECK(IDirect3DTexture9_UnlockRect(tex,i));
        }
        CHECK(IDirect3DDevice9_SetTexture(dev,0,(IDirect3DBaseTexture9*)tex));
        for (unsigned filter=1;filter<=2;filter++) {
            CHECK(IDirect3DDevice9_SetSamplerState(dev,0,D3DSAMP_MINFILTER,filter));
            CHECK(IDirect3DDevice9_SetSamplerState(dev,0,D3DSAMP_MAGFILTER,filter));
            const DWORD sequence[]={0,3,1,3,2,3};
            for (unsigned j=0;j<sizeof sequence/sizeof *sequence;j++) {
                HRESULT hr=IDirect3DDevice9_SetSamplerState(dev,0,D3DSAMP_MIPFILTER,sequence[j]);
                DWORD stored;
                CHECK(IDirect3DDevice9_GetSamplerState(dev,0,D3DSAMP_MIPFILTER,&stored));
                uint32_t exact=sample(dev,target,readback,1), fractional=sample(dev,target,readback,1.45f);
                printf("auto=%d minmag=%u mip=%lu hr=%08lx state=%lu lod2=%06x fractional=%06x\n",
                       autogen,filter,(unsigned long)sequence[j],(unsigned long)hr,(unsigned long)stored,exact,fractional);
            }
        }
        CHECK(IDirect3DDevice9_SetTexture(dev,0,NULL));
        IDirect3DTexture9_Release(tex);
    }
    IDirect3DSurface9_Release(readback); IDirect3DSurface9_Release(target);
    IDirect3DDevice9_Release(dev); IDirect3D9_Release(d3d); DestroyWindow(win);
    return 0;
}
