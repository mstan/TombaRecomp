#ifndef TOMBA_WIDESCREEN_HUD_H
#define TOMBA_WIDESCREEN_HUD_H
#include <stdint.h>

/* SCUS-94236: SetShadeTex's caller plus the builders' saved return addresses
 * identify persistent HUD packets. No screen-position/texture/OT heuristic:
 * these helpers also draw dialogue and world sprites, which must stay put.
 * -1 = left edge, +1 = right edge, 0 = not this HUD. Stack offsets come from
 * each builder's prologue, with the parent frame checked against HUD 8004E468.
 */
static int tomba_hud_edge(uint32_t ra, uint32_t sp,
                          uint32_t (*read_word)(uint32_t)) {
    uint32_t caller;
    switch (ra) {
    case 0x8004E830u: /* AP bar */
        return read_word(sp + 0x2Cu) == 0x8004E4D4u ? 1 : 0;
    case 0x8004E9ACu: /* vitality gauge segments */
        return read_word(sp + 0x3Cu) == 0x8004E4E8u ? -1 : 0;
    case 0x8004EEF4u: /* equipped-item variant */
        return read_word(sp + 0x20u) == 0x8004E4F8u ? -1 : 0;
    case 0x8004F330u: /* single-glyph builder 8004F2CC, frame size 0x28 */
        caller = read_word(sp + 0x20u);
        if (caller == 0x8004E7ACu &&
            read_word(sp + 0x28u + 0x2Cu) == 0x8004E4D4u) return 1;
        if ((caller == 0x8004E62Cu || caller == 0x8004E6B8u ||
             caller == 0x8004E6DCu) &&
            read_word(sp + 0x28u + 0x2Cu) == 0x8004E4C4u) return -1;
        return 0;
    case 0x8004F450u: /* composite builder 8004F3DC, frame size 0x30 */
        caller = read_word(sp + 0x28u);
        if (caller == 0x8004EAD0u &&
            read_word(sp + 0x30u + 0x3Cu) == 0x8004E4E8u) return -1;
        if ((caller == 0x8004EDECu || caller == 0x8004EE18u ||
             caller == 0x8004EE44u || caller == 0x8004EE70u ||
             caller == 0x8004EE9Cu) &&
            read_word(sp + 0x30u + 0x20u) == 0x8004E4F8u) return -1;
        return 0;
    default:
        return 0;
    }
}
#endif
