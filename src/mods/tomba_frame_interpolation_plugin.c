#include "mod_plugins.h"

/*
 * Keep Tomba's guest cadence completely stock. These callbacks only select how
 * frequently PSXrecomp's OpenGL presentation thread blends between the two most
 * recent completed game frames.
 */
static void tomba_frame_rate_set(unsigned frames_per_second) {
    (void)psx_mod_set_frame_interpolation_blend(
        PSX_MOD_FRAME_INTERPOLATION_MOTION_ADAPTIVE);
    (void)psx_mod_set_frame_interpolation(frames_per_second);
}

static void tomba_frame_rate_60_activate(void) {
    tomba_frame_rate_set(60u);
}

static void tomba_frame_rate_120_activate(void) {
    tomba_frame_rate_set(120u);
}

static void tomba_frame_rate_144_activate(void) {
    tomba_frame_rate_set(144u);
}

static void tomba_frame_rate_165_activate(void) {
    tomba_frame_rate_set(165u);
}

static void tomba_frame_rate_display_activate(void) {
    tomba_frame_rate_set(0u);
}

PSX_MOD_CONSTRUCTOR(tomba_register_frame_interpolation_plugin) {
    (void)psx_mod_register_activation_plugin(
        "tomba.framerate.60", tomba_frame_rate_60_activate);
    (void)psx_mod_register_activation_plugin(
        "tomba.framerate.120", tomba_frame_rate_120_activate);
    (void)psx_mod_register_activation_plugin(
        "tomba.framerate.144", tomba_frame_rate_144_activate);
    (void)psx_mod_register_activation_plugin(
        "tomba.framerate.165", tomba_frame_rate_165_activate);
    (void)psx_mod_register_activation_plugin(
        "tomba.framerate.uncapped", tomba_frame_rate_display_activate);
}
