/* SCES-01330 Rev 1, English MAIN. Execute the complete original pad reader,
 * then replace only its digital return value for the original P1 caller.
 * The original outer routine still owns edges, locks, actions and rumble. */
#include "mod_plugins.h"
#include "cpu_state.h"
#include <string.h>

#define PLUGIN "tombi.low-input-latency"
static PSXModDigitalPadReader reader = { sizeof reader };

static int contract(uint32_t address, unsigned length, uint32_t expected) {
    uint32_t hash=2166136261u;
    for(unsigned i=0;i<length;++i)
        hash=(hash^psx_mod_read_byte(address+i))*16777619u;
    return hash==expected;
}

static void reset(void) {
    memset(&reader,0,sizeof reader);reader.struct_size=sizeof reader;
}

static void read_return(struct CPUState *cpu,uint32_t pc) {
    if(pc!=0x800263b4u || cpu->gpr[31]!=0x8001f88cu ||
       psx_mod_read_byte(0x8009f7f0u)!=0 ||
       psx_mod_read_half(0x8009d610u)!=4 ||
       !contract(0x8002623cu,0x180,0xafd11216u) ||
       !contract(0x8001f850u,0x94,0x4ed36982u)) {
        reset();return;
    }
    uint32_t held;
    if(psx_mod_read_digital_pad(0,&reader,cpu->gpr[2],&held))
        cpu->gpr[2]=(uint32_t)(int32_t)(int16_t)(uint16_t)held;
}

PSX_MOD_CONSTRUCTOR(tombi_register_low_input_latency) {
    (void)psx_mod_register_session_reset_plugin(PLUGIN,reset);
    (void)psx_mod_register_activation_plugin(PLUGIN,reset);
    (void)psx_mod_register_savestate_plugin(PLUGIN,reset);
    (void)psx_mod_register_instruction_plugin(PLUGIN,0x800263b4u,
                                             0x03e00008u,read_return);
}
