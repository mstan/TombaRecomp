/* Exercise the real plugin through the same callbacks selected by its package. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "mod_plugins.h"

static PSXModActivationCallback activate, restore;
static PSXModVBlankCallback vblank;
static const char* option;
static int started, enabled, updates, reads, reject_update;
static uint8_t movie;

int psx_mod_register_activation_plugin(const char* id,
                                       PSXModActivationCallback callback) {
    assert(strcmp(id, "tomba.skip-fmv") == 0 && callback && !activate);
    activate = callback;
    return 1;
}

int psx_mod_register_vblank_plugin(const char* id, PSXModVBlankCallback callback) {
    assert(strcmp(id, "tomba.skip-fmv") == 0 && callback && !vblank);
    vblank = callback;
    return 1;
}

int psx_mod_register_savestate_plugin(const char* id,
                                      PSXModActivationCallback callback) {
    assert(strcmp(id, "tomba.skip-fmv") == 0 && callback && !restore);
    restore = callback;
    return 1;
}

int psx_mod_option_value(const char* pkg, const char* feature, const char* id,
                         char* out, uint32_t size) {
    assert(strcmp(pkg, "tomba.enhancement.skip-fmv") == 0);
    assert(strcmp(feature, "skip-fmv") == 0);
    assert(strcmp(id, "preserve-any-percent") == 0);
    if (!option) {
        out[0] = '\0';
        return 0;
    }
    assert(strlen(option) < size);
    strcpy(out, option);
    return 1;
}

int psx_mod_set_auto_skip_fmv(int value) {
    assert(value == 0 || value == 1);
    ++updates;
    if (reject_update) return 0;
    enabled = value;
    return 1;
}

int psx_mod_game_started(void) { return started; }

uint8_t psx_mod_read_byte(uint32_t address) {
    assert(started && address == 0x1F8001CDu);
    ++reads;
    return movie;
}

static void check_skip_all(const char* value) {
    option = value;
    started = 0;
    updates = reads = 0;
    activate();
    assert(enabled == 1 && updates == 1);
    vblank();
    started = 1;
    for (unsigned id = 0; id < 256; ++id) {
        movie = (uint8_t)id;
        vblank();
        restore();
        assert(enabled == 1);
    }
    /* Default mode neither polls guest RAM nor repeatedly calls the setter. */
    assert(reads == 0 && updates == 1);
}

int main(void) {
    assert(activate && vblank && restore);
    check_skip_all(NULL);    /* Existing profile with no new option. */
    check_skip_all("false");
    check_skip_all("invalid");

    option = "true";
    started = 0;
    updates = reads = 0;
    activate();
    assert(enabled == 0 && updates == 1);
    vblank();
    assert(enabled == 0 && reads == 0 && updates == 1);
    started = 1;

    /* Cover the full byte domain: exactly three valid movies are exempt;
     * corrupt/out-of-range IDs must not reach the runtime's table writer. */
    static const int expected_skip[] = {
        1, /* OP_INST: before the title */
        0, /* BOY: opening after New Game */
        1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,
        0, /* MABUTA: post-final-pig ending */
        0, /* END_US: credits */
        1, /* LOGO */
    };
    for (unsigned id = 0; id < 256; ++id) {
        movie = (uint8_t)id;
        vblank();
        int expected = id < sizeof expected_skip / sizeof expected_skip[0]
            ? expected_skip[id] : 0;
        assert(enabled == expected);
    }

    /* Re-enter exempt scenes from skipped scenes, including a state restore.
     * Only transitions call the setter, avoiding per-frame console spam. */
    const uint8_t route[] = {0, 1, 2, 19, 21, 20, 3, 1};
    for (unsigned i = 0; i < sizeof route; ++i) {
        movie = route[i];
        if (i & 1) restore(); else vblank();
        assert(enabled == !(i & 1));
        int previous_updates = updates;
        vblank();
        assert(updates == previous_updates);
    }

    movie = 0;
    reject_update = 1;
    vblank();
    assert(enabled == 0);
    reject_update = 0;
    vblank();
    assert(enabled == 1); /* A failed setter must be retried. */
    started = 0;
    vblank();
    assert(enabled == 0);

    check_skip_all("false"); /* Re-activation clears the previous policy. */
    puts("Tomba FMV skip: defaults, all IDs, transitions, and restores passed");
    return 0;
}
