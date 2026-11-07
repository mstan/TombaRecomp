#ifdef NDEBUG
#undef NDEBUG
#endif
#include "audio_sync.h"
#include "mod_plugins.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static PSXModActivationCallback activate;
static const char *option;
int psx_mod_register_activation_plugin(const char *id,PSXModActivationCallback fn) {
    assert(!strcmp(id,"psx.low-latency-audio")); activate=fn; return 1;
}
int psx_mod_current_option_value(const char *id,char *out,uint32_t size) {
    if (strcmp(id,"target_ms") || !option || strlen(option)>=size) return 0;
    strcpy(out,option); return 1;
}
int main(void) {
    assert(activate);
    psx_audio_sync_set_enabled(0); assert(psx_audio_sync_target(160)==160);
    option=NULL; activate(); assert(psx_audio_sync_target(180)==70);
    option="50"; activate(); assert(psx_audio_sync_target(180)==50);
    /* Editing the provider alone does not alter the running session. */
    option="80"; assert(psx_audio_sync_target(180)==50);
    psx_audio_sync_set_enabled(0); activate(); assert(psx_audio_sync_target(180)==80);
    option="180"; psx_audio_sync_set_enabled(0); activate(); assert(psx_audio_sync_target(180)==180);
    const char *bad[]={"19","181","71","70oops","999999999999999999999999999"};
    for(int i=0;i<5;i++) { option=bad[i]; psx_audio_sync_set_enabled(0); activate(); assert(psx_audio_sync_target(180)==70); }
    psx_audio_sync_set_enabled(0); assert(psx_audio_sync_target(180)==180);
    puts("PASS default70, saved target, next-start activation, validation and OFF fallback");
}
