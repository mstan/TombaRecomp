#include "game_extras.h"

const char *game_get_name(void) {
    return "Tomba!";
}

uint32_t game_get_display_entry(void) {
    return 0x800191E0u;
}

void game_on_init(void) {
    /* TODO: move Tomba-specific init here */
}

void game_on_frame(uint32_t frame_count) {
    (void)frame_count;
    /* TODO: move Tomba-specific per-frame hooks here */
}

int game_handle_arg(const char *key, const char *val) {
    (void)key;
    (void)val;
    return 0;
}

const char *game_arg_usage(void) {
    return NULL;
}

const char *game_get_exe_filename(void) {
    return "SCUS_942.36_no_header";
}

uint32_t game_get_expected_crc32(void) {
    return 0;
}
