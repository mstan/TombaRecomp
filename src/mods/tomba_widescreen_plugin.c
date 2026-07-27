#include "mod_plugins.h"

/*
 * Tomba's game-specific widescreen hooks remain part of generated/runtime
 * code, but their player-facing activation belongs to the mod catalog rather
 * than generic recomp-ui Settings.
 */
static void tomba_widescreen_activate(void) {
    (void)psx_mod_set_fixed_display_aspect(16u, 9u);
}

PSX_MOD_CONSTRUCTOR(tomba_register_widescreen_plugin) {
    (void)psx_mod_register_activation_plugin(
        "tomba.widescreen", tomba_widescreen_activate);
}
