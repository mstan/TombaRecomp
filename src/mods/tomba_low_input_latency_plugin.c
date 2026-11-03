/* Execute the original input path in full. US/EU substitute only the
 * digital reader return for their audited P1 caller. Japan substitutes the
 * cached P1 halfword at the game's original store, after the load delay;
 * its BIOS poll, packed P2 word and initialization remain original.
 * The original outer routine still owns edges, locks, actions and rumble. */
#include "mod_plugins.h"
#include "cpu_state.h"
#include <string.h>
#define PLUGIN "tombi.low-input-latency"
typedef struct TombaInputProfile {
    uint32_t hook,instruction,caller,start,size,hash;
    uint32_t extra,extra_size,extra_hash,field0,field1,kind;
} TombaInputProfile;
#include "tomba_input_profiles.inc"
static PSXModDigitalPadReader reader={sizeof reader};
static const TombaInputProfile *current;
static uint32_t body_hash(uint32_t address,unsigned bytes) {
    uint32_t h=2166136261u;
    for(unsigned i=0;i<bytes;++i)h=(h^psx_mod_read_byte(address+i))*16777619u;
    return h;
}
static void reset(void) {
    memset(&reader,0,sizeof reader);reader.struct_size=sizeof reader;current=0;
}
static void read_return(struct CPUState *cpu,uint32_t pc) {
    const TombaInputProfile *match=0;
    uint32_t base=0,size=0,hash=0,extra=0,extra_size=0,extra_hash=0;
    for(unsigned i=0;i<sizeof input_profiles/sizeof *input_profiles;++i) {
        const TombaInputProfile *p=&input_profiles[i];
        if(p->hook!=pc || p->caller!=cpu->gpr[31])continue;
        if(base!=p->start || size!=p->size) {
            base=p->start;size=p->size;hash=body_hash(base,size);
        }
        if(hash!=p->hash)continue;
        if(extra!=p->extra || extra_size!=p->extra_size) {
            extra=p->extra;extra_size=p->extra_size;extra_hash=body_hash(extra,extra_size);
        }
        if(extra_hash!=p->extra_hash)continue;
        if(p->kind) {
            if(cpu->gpr[4]!=p->field0 || psx_mod_read_word(p->field1)!=1 ||
               psx_mod_read_word(p->caller-8)!=0x0c0081e5u || psx_mod_read_word(p->caller-4)!=0)continue;
        } else if(psx_mod_read_byte(p->field0)!=0 || psx_mod_read_half(p->field1)!=4)continue;
        match=p;break;
    }
    if(!match) {reset();return;}
    if(current!=match) {
        if(!current || current->start!=match->start || current->hash!=match->hash)reset();
        current=match;
    }
    /* Japan's legacy BIOS ReadPad layout swaps the two button bytes.
     * Keep the shared host reader canonical in both directions; only convert
     * the checked guest boundary. Original P2 and SIO data stay untouched. */
    uint32_t legacy=cpu->gpr[2],held;
    if(match->kind)legacy=((legacy>>8)&0xffu)|((legacy&0xffu)<<8);
    if(psx_mod_read_digital_pad(0,&reader,legacy,&held))
        cpu->gpr[2]=match->kind?((held>>8)&0xffu)|((held&0xffu)<<8):
            (uint32_t)(int32_t)(int16_t)(uint16_t)held;
}
PSX_MOD_CONSTRUCTOR(tombi_register_low_input_latency) {
    (void)psx_mod_register_session_reset_plugin(PLUGIN,reset);
    (void)psx_mod_register_activation_plugin(PLUGIN,reset);
    (void)psx_mod_register_savestate_plugin(PLUGIN,reset);
    for(unsigned i=0;i<sizeof input_profiles/sizeof *input_profiles;++i) {
        const TombaInputProfile *p=&input_profiles[i];int duplicate=0;
        for(unsigned j=0;j<i;++j)if(input_profiles[j].hook==p->hook)duplicate=1;
        if(!duplicate)(void)psx_mod_register_instruction_plugin(PLUGIN,p->hook,p->instruction,read_return);
    }
}
