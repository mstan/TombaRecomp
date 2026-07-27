#include "mod_plugins.h"

/*
 * Tomba's FMV teardown addresses stay in game.toml as trusted game metadata.
 * The player-facing switch belongs to the mod catalog rather than generic
 * recomp-ui Settings.
 */
static void tomba_skip_fmv_activate(void) {
    (void)psx_mod_set_auto_skip_fmv(1);
}

PSX_MOD_CONSTRUCTOR(tomba_register_skip_fmv_plugin) {
    (void)psx_mod_register_activation_plugin(
        "tomba.skip-fmv", tomba_skip_fmv_activate);
}
