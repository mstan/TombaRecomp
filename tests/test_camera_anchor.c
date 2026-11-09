/* Exercise the real plugin callbacks: paused frames have no camera entry. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "mod_plugins.h"
#include "cpu_state.h"

static PSXModActivationCallback activate, restore;
static PSXModVBlankCallback vblank;
static PSXModFunctionEntryCallback camera_entry;
static unsigned area, sector;
static int started, camera_active = 1, original_overlay = 1;
static uint32_t follow = 0x1F8000ECu;
static int32_t point = 160 << 16;
static int reveal = 53, anchored, shift, ticks;

int psx_mod_register_activation_plugin(const char* id, PSXModActivationCallback cb) {
    assert(!strcmp(id, "tomba.widescreen") && cb && !activate);
    activate = cb; return 1;
}
int psx_mod_register_savestate_plugin(const char* id, PSXModActivationCallback cb) {
    assert(!strcmp(id, "tomba.widescreen") && cb && !restore);
    restore = cb; return 1;
}
int psx_mod_register_vblank_plugin(const char* id, PSXModVBlankCallback cb) {
    assert(!strcmp(id, "tomba.widescreen") && cb && !vblank);
    vblank = cb; return 1;
}
int psx_mod_register_function_entry_plugin(const char* id, uint32_t addr,
                                          PSXModFunctionEntryCallback cb) {
    assert(!strcmp(id, "tomba.widescreen") && cb);
    if (addr == 0x800636A4u) camera_entry = cb;
    else assert(addr == 0x8005E08Cu);
    return 1;
}
int psx_mod_game_started(void) { return started; }
uint8_t psx_mod_read_byte(uint32_t addr) {
    assert(addr == 0x800A38BCu); return (uint8_t)camera_active;
}
uint16_t psx_mod_read_half(uint32_t addr) {
    switch (addr) {
    case 0x8009BCC8u: return (uint16_t)area;
    case 0x8009BCCAu: return (uint16_t)sector;
    case 0x800A38E4u: return 160;
    default: assert(0); return 0;
    }
}
uint32_t psx_mod_read_word(uint32_t addr) {
    switch (addr) {
    case 0x801168F4u: return original_overlay ? 0x27BDFFE8u : 0;
    case 0x801169ECu: return original_overlay ? 0x0C00B3BEu : 0;
    case 0x800A38ECu: return follow;
    case 0x1F8000ECu: return (uint32_t)point;
    default: assert(0); return 0;
    }
}
int32_t psx_mod_widescreen_view_x_margin(void) { return reveal; }
void psx_mod_set_widescreen_view_anchor(int enabled, int32_t value) {
    anchored = enabled; shift = value;
}
void tomba_widescreen_residency_activate(void) {}
void tomba_widescreen_scripts_activate(void) {}
void tomba_widescreen_scripts_tick(void) { ++ticks; }
void psx_mod_set_adaptive_backdrop_preload(int value) { assert(value == 1); }
void psx_mod_tag_hud_primitive(uint32_t primitive, int edge) {
    (void)primitive; (void)edge;
}
void psx_mod_tag_world_primitive(uint32_t primitive, int world) {
    (void)primitive; (void)world;
}
int psx_mod_option_value(const char* pkg, const char* feature, const char* option,
                         char* out, uint32_t capacity) {
    (void)pkg; (void)feature; (void)option; (void)capacity;
    out[0] = 0; return 0;
}
int psx_mod_set_fixed_display_aspect(uint32_t num, uint32_t den) {
    assert(num == 16 && den == 9); return 1;
}
int psx_mod_set_adaptive_display_aspect(uint32_t num, uint32_t den) {
    assert(num == 34 && den == 9); return 1;
}

int main(void) {
    static CPUState cpu;
    assert(activate && restore && vblank && camera_entry);
    activate(); vblank(); assert(!anchored);
    started = 1;
    cpu.gpr[31] = 0x8002A1E4u; cpu.gpr[4] = 0x1F8000C0u;
    cpu.gpr[5] = 0x1F800060u; cpu.gpr[6] = 0x1F800068u;
    camera_entry(&cpu, 0x800636A4u);
    assert(anchored && shift == -53);
    /* Pausing, resizing and restoring must refresh without a builder call. */
    for (int i = 0; i < 10; ++i) {
        anchored = 0; reveal = i % 2 ? 267 : 293;
        vblank(); assert(anchored && shift == -reveal);
    }
    anchored = 0; restore(); assert(anchored && shift == -reveal);
    point = 200 << 16; vblank(); assert(shift == 40 - reveal);
    point = 1200 << 16; vblank(); assert(anchored && shift == 0);
    reveal = 0; vblank(); assert(shift == 0);
    /* A room/sector transition or invalid camera clears the host origin. */
    area = 2; restore(); assert(!anchored);
    area = 0; sector = 1; vblank(); assert(!anchored);
    sector = 0; original_overlay = 0; vblank(); assert(!anchored);
    original_overlay = 1; camera_active = 0; vblank(); assert(!anchored);
    camera_active = 1; follow = 0x1F8000F4u; vblank(); assert(!anchored);
    follow = 0x1F8000ECu; started = 0; vblank(); assert(!anchored);
    assert(ticks == 21);
    puts("PASS: camera anchor survives pause/resize/restore and excludes other scenes");
    return 0;
}
