#include "mod_plugins.h"
#include "cpu_state.h"
#include "tomba_widescreen_hud.h"
#include "tomba_widescreen_sprites.h"
#include "tomba_widescreen_view.h"
#include "tomba_widescreen_camera.h"
#include "tomba_widescreen_scripts.h"
#include "tomba_widescreen_scene.h"

/*
 * Tomba's game-specific widescreen hooks remain part of generated/runtime
 * code, but their player-facing activation belongs to the mod catalog rather
 * than generic recomp-ui Settings.  The renderer is native-wide: it grows the
 * compositor surface and its cull margin, rather than stretching the 320px
 * framebuffer. Start from a 16:9 window, then let Fit follow every resize
 * up to the validated 34:9 limit. Fixed views use this same renderer.
 */
#define PKG "tomba.enhancement.widescreen"
#define FEATURE "widescreen"
static int tomba_widescreen_enabled;
static uint32_t tomba_widescreen_frame, tomba_widescreen_world_frame;
static int tomba_widescreen_world_seen;

static int tomba_widescreen_world_scene_present(void) {
    if (!tomba_widescreen_enabled) return 0;
    if (!psx_mod_game_started()) return 0;
    return tomba_widescreen_world_scene(
        psx_mod_read_half(0x8009BCC8u), psx_mod_read_half(0x8009BCCAu),
        tomba_widescreen_world_seen, tomba_widescreen_frame,
        tomba_widescreen_world_frame);
}
/* Event-title glyphs use the persistent layer-8 pool, including the untextured
 * GTE jingle quads. They are UI, not newly revealed terrain. Preserve the
 * underlying scene's presentation instead of forcing every event to 4:3.
 * The pool base/stride/count already belong to the checked residency profile. */
static int tomba_widescreen_retained_scene(void) {
    if (!tomba_widescreen_enabled) return 0;
    if (!psx_mod_game_started()) return 0;
    for (unsigned i = 0; i < 45; ++i) {
        uint32_t object = 0x800B0B88u + i * 0xD4u;
        if (psx_mod_read_byte(object) == 1 &&
            psx_mod_read_byte(object + 2) == 1 &&
            psx_mod_read_half(object + 8) == 0x7D16u &&
            (psx_mod_read_byte(object + 0x1C) & 0x80))
            return PSX_MOD_SCENE_HOLD;
    }
    /* Guest objects can finish before their submitted frontbuffer is replaced. */
    return PSX_MOD_SCENE_UNTIL_FLIP;
}
extern void tomba_widescreen_residency_activate(void);

/* Moving the guest camera itself under-shifts slower parallax backdrops.
 * Refresh the frame-local screen origin even when pause/dialogue bypasses
 * the native camera builder. Revalidate the scene on every refresh. */
static void tomba_widescreen_refresh_anchor(void) {
    if (!tomba_widescreen_enabled) return;
    if (!psx_mod_game_started()) goto disable;
    unsigned area = psx_mod_read_half(0x8009BCC8u);
    unsigned sector = psx_mod_read_half(0x8009BCCAu);
    if (area != 0 || sector != 0) goto disable;
    /* Overlay addresses are reused; require the original area-0 handler. */
    if (psx_mod_read_word(0x801168F4u) != 0x27BDFFE8u ||
        psx_mod_read_word(0x801169ECu) != 0x0C00B3BEu) goto disable;
    const uint32_t camera = 0x800A38B8u;
    if (psx_mod_read_byte(camera + 4) != 1) goto disable;
    uint32_t follow = psx_mod_read_word(camera + 0x34);
    if (follow != 0x1F8000ECu) goto disable;
    int32_t original = (int32_t)psx_mod_read_word(follow);
    int left = (int16_t)psx_mod_read_half(camera + 0x2C);
    int32_t shift = tomba_widescreen_camera_shift(area, sector, left,
        original, psx_mod_widescreen_view_x_margin());
    psx_mod_set_widescreen_view_anchor(1, shift);
    return;
disable:
    psx_mod_set_widescreen_view_anchor(0, 0);
}

static void tomba_widescreen_anchor_camera(CPUState* cpu, uint32_t address) {
    (void)address;
    if (cpu->gpr[31] != 0x8002A1E4u || cpu->gpr[4] != 0x1F8000C0u ||
        cpu->gpr[5] != 0x1F800060u || cpu->gpr[6] != 0x1F800068u) return;
    tomba_widescreen_refresh_anchor();
}

static void tomba_widescreen_tick(void) {
    ++tomba_widescreen_frame;
    tomba_widescreen_scripts_tick();
    tomba_widescreen_refresh_anchor();
}

static void tomba_widescreen_tag_hud(CPUState* cpu, uint32_t address) {
    (void)address;
    if (!tomba_widescreen_enabled) return;
    int edge = tomba_hud_edge(cpu->gpr[31], cpu->gpr[29], psx_mod_read_word);
    psx_mod_tag_hud_primitive(cpu->gpr[4], edge);
    int world = tomba_is_world_sprite(cpu->gpr[31]);
    psx_mod_tag_world_primitive(cpu->gpr[4], world);
    if (world || edge) {
        tomba_widescreen_world_seen = 1;
        tomba_widescreen_world_frame = tomba_widescreen_frame;
    }
}

static void tomba_widescreen_activate(void) {
    char aspect[16];
    tomba_widescreen_enabled = 1;
    psx_mod_set_world_scene_predicate(tomba_widescreen_world_scene_present);
    psx_mod_set_retained_scene_predicate(tomba_widescreen_retained_scene);
    tomba_widescreen_residency_activate();
    tomba_widescreen_scripts_activate();
    psx_mod_set_adaptive_backdrop_preload(1);

    if (!psx_mod_option_value(PKG, FEATURE, "aspect", aspect, sizeof aspect))
        strcpy(aspect, "Fit");

    TombaWidescreenView view = tomba_widescreen_view(aspect);
    (void)psx_mod_set_fixed_display_aspect(view.numerator, view.denominator);
    if (view.fit)
        (void)psx_mod_set_adaptive_display_aspect(
            TOMBA_WIDESCREEN_FIT_MAX_NUMERATOR,
            TOMBA_WIDESCREEN_FIT_MAX_DENOMINATOR);
}

static void tomba_widescreen_restore(void) {
    tomba_widescreen_world_seen = 0;
    tomba_widescreen_tick();
}

PSX_MOD_CONSTRUCTOR(tomba_register_widescreen_plugin) {
    (void)psx_mod_register_function_entry_plugin(
        "tomba.widescreen", 0x800636A4u, tomba_widescreen_anchor_camera);
    (void)psx_mod_register_function_entry_plugin(
        "tomba.widescreen", 0x8005E08Cu, tomba_widescreen_tag_hud);
    (void)psx_mod_register_activation_plugin(
        "tomba.widescreen", tomba_widescreen_activate);
    (void)psx_mod_register_vblank_plugin(
        "tomba.widescreen", tomba_widescreen_tick);
    (void)psx_mod_register_savestate_plugin(
        "tomba.widescreen", tomba_widescreen_restore);
}
