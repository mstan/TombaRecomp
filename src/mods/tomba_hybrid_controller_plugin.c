#include "mod_plugins.h"

/*
 * Keep Tomba's game-owned Hybrid Controller policy out of the generic
 * controller selector. The activation runs after launcher/settings resolution,
 * so this deliberately wins over the normal Analog / D-Pad choice for Player 1
 * only when the corresponding mod feature is enabled.
 */
static void tomba_hybrid_controller_activate(void) {
    (void)psx_mod_set_controller_mode_override(
        0u, PSX_MOD_CONTROLLER_HYBRID);
}

PSX_MOD_CONSTRUCTOR(tomba_register_hybrid_controller_plugin) {
    (void)psx_mod_register_activation_plugin(
        "tomba.hybrid-controller", tomba_hybrid_controller_activate);
}
