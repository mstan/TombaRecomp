#include "mod_plugins.h"

#include <string.h>

#define PKG "tomba.enhancement.skip-fmv"
#define FEATURE "skip-fmv"
#define PLUGIN "tomba.skip-fmv"
#define MOVIE_ID_ADDRESS 0x1F8001CDu

static int s_preserve_any_percent;
static int s_skip_enabled;

static void tomba_skip_fmv_set_enabled(int enabled) {
    if (enabled != s_skip_enabled && psx_mod_set_auto_skip_fmv(enabled))
        s_skip_enabled = enabled;
}

static void tomba_skip_fmv_update(void) {
    uint8_t movie;
    if (!s_preserve_any_percent)
        return;

    /* The scratchpad does not contain a Tomba movie ID until the game starts.
     * VBlank plugins run before the runtime's skip/mute/pacing decision, so
     * exempt movies retain normal video AND audio, even after a skipped FMV. */
    if (!psx_mod_game_started()) {
        tomba_skip_fmv_set_enabled(0);
        return;
    }
    movie = psx_mod_read_byte(MOVIE_ID_ADDRESS);

    /* SCUS-94236: movie -> asset map at 8007775C, asset indices at 80078F80,
     * CD locations at 800791A0. Verified against the original disc's movies:
     *   0 = OP_INST.STR (title opening, 1414 frames)
     *  19 = MABUTA.STR  (post-final-pig ending, 316 frames)
     *  20 = END_US.STR  (credits, 943 frames)
     * ID 1 (BOY.STR, New Game) and ID 21 (LOGO.STR) still skip. Unknown IDs
     * fail closed instead of letting the runtime index beyond the table. */
    tomba_skip_fmv_set_enabled(
        movie < 22u && movie != 0u && movie != 19u && movie != 20u);
}

/*
 * Tomba's FMV teardown addresses stay in game.toml as trusted game metadata.
 * The player-facing switch belongs to the mod catalog rather than generic
 * recomp-ui Settings.
 */
static void tomba_skip_fmv_activate(void) {
    char value[8];
    s_preserve_any_percent = psx_mod_option_value(
        PKG, FEATURE, "preserve-any-percent", value, sizeof value) &&
        strcmp(value, "true") == 0;
    s_skip_enabled = -1;
    /* Preserve the existing skip-all behavior for old or untouched profiles.
     * Exception mode waits for the first guest VBlank to identify the movie. */
    tomba_skip_fmv_set_enabled(!s_preserve_any_percent);
}

PSX_MOD_CONSTRUCTOR(tomba_register_skip_fmv_plugin) {
    (void)psx_mod_register_activation_plugin(
        PLUGIN, tomba_skip_fmv_activate);
    (void)psx_mod_register_vblank_plugin(PLUGIN, tomba_skip_fmv_update);
    (void)psx_mod_register_savestate_plugin(PLUGIN, tomba_skip_fmv_update);
}
