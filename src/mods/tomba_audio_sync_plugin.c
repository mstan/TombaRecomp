/* Host output policy only; shared by the official regional players. */
#include "audio_sync.h"
#include "mod_plugins.h"
#include <errno.h>
#include <stdlib.h>
#include <string.h>
static void activate_audio_sync(void) {
    char value[32], *end;
    psx_audio_sync_set_enabled(1);
    /* target_ms is an absolute buffer size, never a reduction. Only the
     * committed plan is read; editing options cannot retarget a running device. */
    if (psx_mod_current_option_value("target_ms", value, sizeof(value))) {
        errno = 0;
        const long target = strtol(value, &end, 10);
        if (!errno && end != value && !*end && target >= PSX_AUDIO_SYNC_MIN_MS &&
            target <= PSX_AUDIO_SYNC_MAX_MS)
            (void)psx_audio_sync_set_target((int)target);
    }
    if (psx_mod_current_option_value("diagnostics", value, sizeof(value)))
        psx_audio_sync_set_diagnostics(!strcmp(value,"true") || !strcmp(value,"1"));
}
PSX_MOD_CONSTRUCTOR(tomba_register_audio_sync_plugin) {
    (void)psx_mod_register_activation_plugin("psx.low-latency-audio", activate_audio_sync);
}
