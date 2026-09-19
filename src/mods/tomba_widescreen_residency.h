#ifndef TOMBA_WIDESCREEN_RESIDENCY_H
#define TOMBA_WIDESCREEN_RESIDENCY_H
#include <stdint.h>

/* Area 1's roof transition is player-X 2925/2926 (overlay 80115E2C/15F14).
 * Its object banks are spatial neighbors, not alternate versions of one room.
 * Camera X is the native 320-pixel view's left edge. Include the cull guard. */
static inline unsigned tomba_roof_resident_mask(int camera_x, int margin,
                                                unsigned logical_sector) {
    if (logical_sector > 1) return 0;
    unsigned mask = 1u << logical_sector;
    if (margin > 0 && (int64_t)camera_x - margin <= 2926 &&
        (int64_t)camera_x + 320 + margin >= 2925) mask = 3;
    return mask;
}

static inline int tomba_roof_keep_group(int group, unsigned mask) {
    /* -1 is shared by banks 0 and 1. Other groups are not owned by this rule. */
    if (group < 0 || group > 1) return 1;
    return (mask & (1u << group)) != 0;
}
#endif
