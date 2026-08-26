#include "mod_plugins.h"

static uint32_t tomba_hybrid_controller_mode = PSX_MOD_CONTROLLER_ANALOG;

static uint32_t tomba_hybrid_controller_policy(
    const PSXModControllerInput* input) {
    if (input) {
        if (input->stick_active) {
            tomba_hybrid_controller_mode = PSX_MOD_CONTROLLER_ANALOG;
        } else if (input->dpad_active) {
            tomba_hybrid_controller_mode = PSX_MOD_CONTROLLER_DIGITAL;
        }
    }
    return tomba_hybrid_controller_mode;
}

static void tomba_hybrid_controller_activate(void) {
    tomba_hybrid_controller_mode = PSX_MOD_CONTROLLER_ANALOG;
    (void)psx_mod_set_controller_presentation_policy(
        0u, tomba_hybrid_controller_policy,
        PSX_MOD_CONTROLLER_ANALOG, 1);
}

PSX_MOD_CONSTRUCTOR(tomba_register_hybrid_controller_plugin) {
    (void)psx_mod_register_activation_plugin(
        "tomba.hybrid-controller", tomba_hybrid_controller_activate);
}
