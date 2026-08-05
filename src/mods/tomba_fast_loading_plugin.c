#include "mod_plugins.h"

#include <stdlib.h>
#include <string.h>

/*
 * Host pacing only. Guest-visible CD timing moved to its own mod
 * (tomba.enhancement.cd-speed) so a player can take faster loads WITHOUT the
 * game speeding up during them -- the speed-up is what breaks timing-based
 * routes (GH TombaRecomp#5). The two are independent now; enabling both is
 * allowed and simply applies both.
 */
#define PKG "tomba.enhancement.fast-loading"
#define FEATURE "fast-loading"

static long option_number(const char* id, long fallback) {
    char text[32] = "";
    if (!psx_mod_option_value(PKG, FEATURE, id, text, sizeof text) || !text[0])
        return fallback;
    char* end = NULL;
    const long value = strtol(text, &end, 10);
    if (!end || *end != '\0' || value < 0) return fallback;
    return value;
}

static int option_flag(const char* id) {
    char text[16] = "";
    return psx_mod_option_value(PKG, FEATURE, id, text, sizeof text) &&
           strcmp(text, "true") == 0;
}

static void tomba_fast_loading_activate(void) {
    /* Uncapped is expressed to the runtime as multiplier 0. Multiplier 1 is
     * authentic pacing -- a legal setting, so a player can park the value there
     * without having to disable the whole feature. */
    const unsigned multiplier =
        option_flag("uncapped") ? 0u : (unsigned)option_number("multiplier", 4);
    (void)psx_mod_set_load_acceleration(multiplier, 0u);
}

PSX_MOD_CONSTRUCTOR(tomba_register_fast_loading_plugin) {
    (void)psx_mod_register_activation_plugin(
        "tomba.fast-loading", tomba_fast_loading_activate);
}
