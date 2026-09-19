#include "mod_plugins.h"

#include <stdlib.h>
#include <string.h>

/*
 * Keep Tomba's optional load acceleration in one default-off mod feature.
 * This changes host wall-clock pacing only; it deliberately does not touch the
 * emulated CD timing divisor because that changes guest-observable timing.
 */
#define PKG "tomba.enhancement.fast-loading"
#define FEATURE "fast-loading"

static void tomba_fast_loading_activate(void) {
    char speed[16];
    uint32_t multiplier = 4u;

    if (psx_mod_option_value(
            PKG, FEATURE, "speed", speed, sizeof speed)) {
        if (strcmp(speed, "uncapped") == 0) {
            multiplier = 0u;
        } else {
            char* end = speed;
            const unsigned long parsed = strtoul(speed, &end, 10);
            if (end != speed && *end == '\0')
                multiplier = (uint32_t)parsed;
        }
    }

    /* Stop on the first frame where the sustained-load predicate clears.
     * This avoids carrying acceleration into speedrun inputs after a load. */
    (void)psx_mod_set_load_acceleration(multiplier, 0u);
}

PSX_MOD_CONSTRUCTOR(tomba_register_fast_loading_plugin) {
    (void)psx_mod_register_activation_plugin(
        "tomba.fast-loading", tomba_fast_loading_activate);
}
