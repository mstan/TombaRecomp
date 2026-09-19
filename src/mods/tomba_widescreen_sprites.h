#ifndef TOMBA_WIDESCREEN_SPRITES_H
#define TOMBA_WIDESCREEN_SPRITES_H
#include <stdint.h>

/* SCUS-94236's transformed world-sprite builder, calling SetShadeTex.
 * A world billboard can sort BEFORE the first Gouraud polygon. That does not
 * make it a screen-space backdrop: stretching it creates detached scenery.
 * Keep this producer-based, never inferred from screen X, CLUT or OT rank. */
static inline int tomba_is_world_sprite(uint32_t shade_tex_return) {
    return shade_tex_return == 0x8004A170u;
}
#endif
