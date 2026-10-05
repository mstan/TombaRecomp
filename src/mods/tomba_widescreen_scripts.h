#pragma once
#include <stdint.h>

/* Retail 80022E44 predicate, including its unsigned halfword arithmetic.
 * Script visibility has a fixed 64px guard regardless of the rendered aspect. */
static inline int tomba_script_visible(int x, int y, int camera_x, int camera_y) {
    return (uint16_t)(x - camera_x + 64) < 449u &&
           (uint16_t)(camera_y - y + 64) < 369u;
}
void tomba_widescreen_scripts_activate(void);
void tomba_widescreen_scripts_tick(void);
