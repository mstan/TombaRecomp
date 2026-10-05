/* Hardware-boundary fixture for the native transfer body. The Python oracle
 * runs the original MIPS driver against the same DMA completion contract. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdint.h>
static uint8_t *sound;
static const uint8_t *source;
static uint32_t *state, cursor;
static uint32_t r32(uint32_t a) {
    assert(a>=0x80097840u && a<=0x80097C3Cu);
    const uint8_t *p=source+(a-0x80097840u);
    return (uint32_t)p[0] | (uint32_t)p[1]<<8 | (uint32_t)p[2]<<16 | (uint32_t)p[3]<<24;
}
static void w16(uint32_t a, uint16_t v) {
    assert(a==0x80097C60u); state[0]=(state[0]&0xFFFF0000u)|v;
}
static void w32(uint32_t a, uint32_t v) {
    assert(a==0x80097C98u || a==0x80097C9Cu || a==0x80097CA0u);
    state[1+(a-0x80097C98u)/4]=v;
}
static uint16_t spu_ctrl_read(void) { return (uint16_t)state[5]; }
static void spu_write(uint32_t a, uint32_t v) {
    if(a==0x1F801DA6u) { state[4]=v; cursor=v*8; }
    else { assert(a==0x1F801DAAu); state[5]=v; }
}
static void spu_dma_write(uint32_t v) {
    for(unsigned i=0;i<4;i++) sound[cursor++&0x7FFFF]=(uint8_t)(v>>(8*i));
}
/* The framework's psx_mod_spu_upload contract at the hardware boundary:
 * transfer address, DMA-write mode, words through the SPU DMA path, stop. */
static int psx_mod_spu_upload(uint32_t spu, uint32_t src, uint32_t bytes, int stop) {
    spu_write(0x1F801DA6u,spu>>3);
    uint16_t ctrl=spu_ctrl_read();
    spu_write(0x1F801DAAu,(ctrl&~0x30u)|0x20u);
    for(uint32_t j=0;j<bytes;j+=4) spu_dma_write(r32(src+j));
    if(stop) spu_write(0x1F801DAAu,ctrl&~0x30u);
    return 1;
}
#include "../src/mods/tomba_seamless_spu.h"
#ifdef _WIN32
__declspec(dllexport)
#endif
void seamless_reverb_fixture(uint32_t begin, uint8_t *ram,
                             const uint8_t *buffer, uint32_t *registers) {
    assert(begin>=0x1010 && begin<0x80000 && !(begin&7));
    sound=ram;source=buffer;state=registers;
    tomba_reverb_transfer(begin);
}
