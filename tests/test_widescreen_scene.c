#include "../src/mods/tomba_widescreen_scene.h"
#undef NDEBUG
#include <assert.h>
#include <stdio.h>
int main(void) {
    /* No area alone may turn a menu into a world scene. */
    assert(!tomba_widescreen_world_scene(4,2,0,100,100));
    assert(tomba_widescreen_world_scene(4,2,1,100,100));
    assert(tomba_widescreen_world_scene(4,2,1,101,100));
    assert(!tomba_widescreen_world_scene(4,2,1,102,100));
    /* Deliberate 2D rooms and every other scene still defer to the renderer. */
    for (unsigned a=0;a<20;a++) for (unsigned b=0;b<32;b++)
        if (a!=4 || b!=2) assert(!tomba_widescreen_world_scene(a,b,1,100,100));
    assert(!tomba_widescreen_world_scene(4,2,1,99,100));
    assert(tomba_widescreen_world_scene(4,2,1,0,UINT32_MAX));
    puts("PASS scene scope, active world requirement, menu expiry and frame wrap");
}
