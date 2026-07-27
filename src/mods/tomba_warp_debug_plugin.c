#include "mod_plugins.h"

#define TOMBA_WARP_DEBUG_FLAG 0x1F8001B4u

/*
 * The stock executable clears this scratchpad halfword during startup and
 * checks its low byte while entering the game. Reassert the documented value
 * on guest VBlank so the behavior is independent of host presentation and is
 * in place before the player starts a game.
 */
static void tomba_warp_debug_vblank(void) {
    if (!psx_mod_game_started())
        return;
    if (psx_mod_read_byte(TOMBA_WARP_DEBUG_FLAG) != 1u)
        psx_mod_write_byte(TOMBA_WARP_DEBUG_FLAG, 1u);
}

PSX_MOD_CONSTRUCTOR(tomba_register_warp_debug_plugin) {
    (void)psx_mod_register_vblank_plugin(
        "tomba.warp-debug", tomba_warp_debug_vblank);
}
