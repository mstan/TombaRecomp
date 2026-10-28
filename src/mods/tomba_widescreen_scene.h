#ifndef TOMBA_WIDESCREEN_SCENE_H
#define TOMBA_WIDESCREEN_SCENE_H
#include <stdint.h>

/* The mansion south exterior has real 3D terrain in front of a scrolling
 * 448px tiled backdrop. Its edge crossing the configured reveal is not a
 * transition to a finite 2D room. Other sections retain renderer inference.
 * Require a recent gameplay HUD/world submission so menus do not inherit it. */
static inline int tomba_widescreen_world_scene(unsigned area, unsigned section,
        int world_seen, uint32_t frame, uint32_t last_world_frame) {
    return area == 4 && section == 2 && world_seen &&
        frame - last_world_frame <= 1u;
}
#endif
