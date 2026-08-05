#include "mod_plugins.h"

#include <stdlib.h>
#include <string.h>

/*
 * Guest-visible CD drive speed, split out of the old combined fast-loading
 * choice. This shortens loads without speeding the game up, which is what a
 * timing-sensitive route needs (GH TombaRecomp#5). The multiplier is a free
 * integer rather than a curated 2x/4x list so players can find the highest
 * speed this game tolerates; the runtime floors the divided sector delay and
 * leaves XA streaming authentic, so no value here can storm or pitch-shift.
 */
#define PKG "tomba.enhancement.cd-speed"
#define FEATURE "cd-speed"

static long option_number(const char* id, long fallback) {
    char text[32] = "";
    if (!psx_mod_option_value(PKG, FEATURE, id, text, sizeof text) || !text[0])
        return fallback;
    char* end = NULL;
    const long value = strtol(text, &end, 10);
    if (!end || *end != '\0' || value <= 0) return fallback;
    return value;
}

static int option_flag(const char* id) {
    char text[16] = "";
    return psx_mod_option_value(PKG, FEATURE, id, text, sizeof text) &&
           strcmp(text, "true") == 0;
}

static void tomba_cd_speed_activate(void) {
    if (option_flag("instant")) {
        /* Divisor 0 selects the bounded instant scheduler; the budget is the
         * only thing that matters in that mode. */
        (void)psx_mod_set_disc_speed(
            0u, (unsigned)option_number("instant_budget", 32));
        return;
    }
    (void)psx_mod_set_disc_speed((unsigned)option_number("multiplier", 4), 0u);
}

PSX_MOD_CONSTRUCTOR(tomba_register_cd_speed_plugin) {
    (void)psx_mod_register_activation_plugin(
        "tomba.cd-speed", tomba_cd_speed_activate);
}
