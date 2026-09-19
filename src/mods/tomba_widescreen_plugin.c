#include "mod_plugins.h"
#include "cpu_state.h"
#include "tomba_widescreen_hud.h"
#include "tomba_widescreen_sprites.h"
#include "tomba_widescreen_view.h"

/*
 * Tomba's game-specific widescreen hooks remain part of generated/runtime
 * code, but their player-facing activation belongs to the mod catalog rather
 * than generic recomp-ui Settings.  The renderer is native-wide: it grows the
 * compositor surface and its cull margin, rather than stretching the 320px
 * framebuffer. Start from a 16:9 window, then let Fit follow every resize
 * without an upper aspect-ratio limit. Fixed views use this same renderer.
 */
#define PKG "tomba.enhancement.widescreen"
#define FEATURE "widescreen"
static int tomba_widescreen_enabled;
extern void tomba_widescreen_residency_activate(void);

static void tomba_widescreen_tag_hud(CPUState* cpu, uint32_t address) {
    (void)address;
    if (!tomba_widescreen_enabled) return;
    psx_mod_tag_hud_primitive(cpu->gpr[4],
        tomba_hud_edge(cpu->gpr[31], cpu->gpr[29], psx_mod_read_word));
    psx_mod_tag_world_primitive(cpu->gpr[4], tomba_is_world_sprite(cpu->gpr[31]));
}

static void tomba_widescreen_activate(void) {
    char aspect[16];
    tomba_widescreen_enabled = 1;
    tomba_widescreen_residency_activate();
    psx_mod_set_adaptive_backdrop_preload(1);

    if (!psx_mod_option_value(PKG, FEATURE, "aspect", aspect, sizeof aspect))
        strcpy(aspect, "Fit");

    TombaWidescreenView view = tomba_widescreen_view(aspect);
    (void)psx_mod_set_fixed_display_aspect(view.numerator, view.denominator);
    if (view.fit)
        (void)psx_mod_set_adaptive_display_aspect(0u, 0u);
}

PSX_MOD_CONSTRUCTOR(tomba_register_widescreen_plugin) {
    (void)psx_mod_register_function_entry_plugin(
        "tomba.widescreen.hud", 0x8005E08Cu, tomba_widescreen_tag_hud);
    (void)psx_mod_register_activation_plugin(
        "tomba.widescreen", tomba_widescreen_activate);
}
