/* Hold only the original selector's idle timer. This is a product policy,
 * not a test progress/inventory injection. Original BIN/CUE and code stay
 * unchanged; the manual Cross path still performs the original LoadExec. */
#include "mod_plugins.h"
#include "eu_boot_profile.inc"

static void selector_tick(void) {
    if (psx_mod_read_word(TOMBI_SELECTOR_START)!=0x27BDFF88u ||
        psx_mod_read_word(TOMBI_SELECTOR_BRANCH)!=0x14620039u) return;
    uint32_t hash=2166136261u;
    for (uint32_t pc=TOMBI_SELECTOR_START;pc<TOMBI_SELECTOR_END;pc+=4) {
        uint32_t word=psx_mod_read_word(pc);
        for(unsigned i=0;i<4;++i){hash=(hash^(word&255u))*16777619u;word>>=8;}
    }
    if(hash!=TOMBI_SELECTOR_HASH) return;
    const uint32_t remaining=psx_mod_read_word(TOMBI_SELECTOR_TIMER);
    if(remaining>0 && remaining<=1000)
        psx_mod_write_word(TOMBI_SELECTOR_TIMER,1000);
}

PSX_MOD_CONSTRUCTOR(tombi_register_language_confirmation) {
    psx_mod_register_vblank_plugin("tombi.language-confirmation",selector_tick);
}
