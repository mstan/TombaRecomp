#include "game_extras.h"
#include "debug_server.h"
#include "psx_runtime.h"

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

uint32_t game_get_entry_point(void) {
    return 0x8006B58Cu;
}

void game_fill_frame_record(void *record) {
    PSXFrameRecord *r = (PSXFrameRecord *)record;
    /* Tomba-specific state: fill game_data[32] with relevant RAM values.
     * Addresses TBD after Ghidra analysis of Tomba's RAM layout. */
    (void)r;
}

int game_handle_debug_cmd(const char *cmd, int id, const char *json) {
    (void)cmd; (void)id; (void)json;
    /* Tomba-specific commands:
     * - "entity_list" to dump all 200 entity slots
     * - "player_state" for position/health/inventory
     * - "area_info" for current area/map
     * These will be implemented after Ghidra identifies the relevant addresses. */
    return 0;  /* not handled */
}

void game_post_frame(uint32_t frame_count) {
    (void)frame_count;
}
