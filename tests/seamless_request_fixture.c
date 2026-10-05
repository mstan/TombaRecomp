/* Offline original-disc audit seam. Exercise the production preflight against
 * queues built by the original MIPS list selector, without running the game or
 * installing resources. No game assets are part of this fixture. */
#include "mod_plugins.h"
#undef PSX_MOD_CONSTRUCTOR
#define PSX_MOD_CONSTRUCTOR(name) static void name(void)
#include "../src/mods/tomba_seamless.c"

#if defined(_WIN32)
#define FIXTURE_EXPORT __declspec(dllexport)
#else
#define FIXTURE_EXPORT __attribute__((visibility("default")))
#endif

static const uint8_t *fixture_ram, *fixture_scratch;
uint8_t psx_mod_read_byte(uint32_t address) {
    address &= 0x1FFFFFFFu;
    if(address < 0x200000u) return fixture_ram[address];
    if(address >= 0x1F800000u && address < 0x1F800400u)
        return fixture_scratch[address-0x1F800000u];
    return 0;
}
uint16_t psx_mod_read_half(uint32_t address) {
    return psx_mod_read_byte(address) | (uint16_t)psx_mod_read_byte(address+1)<<8;
}
uint32_t psx_mod_read_word(uint32_t address) {
    return psx_mod_read_half(address) | (uint32_t)psx_mod_read_half(address+2)<<16;
}
FIXTURE_EXPORT int seamless_fixture_load_pack(const char *path) {
    return load_pack(path);
}
FIXTURE_EXPORT int seamless_fixture_plan(const uint8_t *ram_bytes,
                                          const uint8_t *scratch_bytes,
                                          unsigned index) {
    Request request;
    fixture_ram=ram_bytes;
    fixture_scratch=scratch_bytes;
    return index < 128 && plan_request(index,&request);
}
