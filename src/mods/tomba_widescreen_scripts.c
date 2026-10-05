#include "tomba_widescreen_scripts.h"
#include "tomba_dispatch.h"
#include "mod_plugins.h"
#include "interrupts.h"

static int enabled;

static int script_visibility(CPUState* cpu, uint32_t phys) {
    if (!enabled || phys != 0x22E44u || !psx_mod_game_started()) return 0;
    uint32_t ra = cpu->gpr[31];
    /* Both script interpreters have the same "is actor on screen" opcode.
     * This is a logic query, not a request to widen cutscene movement. */
    if ((ra != 0x8003D8B8u && ra != 0x8003E828u) ||
        psx_mod_read_word(ra - 8) != 0x0C008B91u) return 0;
    uint32_t actor = cpu->gpr[4];
    if (actor < 0x80098000u || actor > 0x801FFFB8u ||
        !psx_mod_read_byte(actor)) return 0;
    uint32_t position = psx_mod_read_word(actor + 0x40);
    if (position < 0x80098000u || position > 0x801FFFFCu) return 0;

    /* Keep the original wide draw admission/queue effects. The synthetic
     * return bypasses this query hook; defer snapshots until registers are
     * restored because the host continuation cannot be serialized. */
    CPUState saved = *cpu;
    psx_snapshot_host_call_begin();
    cpu->gpr[31] = 0x8000FE00u;
    psx_dispatch_call(cpu, 0x80022E44u, cpu->gpr[31]);
    *cpu = saved;
    psx_snapshot_host_call_end();

    int visible = tomba_script_visible(
        (int16_t)psx_mod_read_half(position + 2),
        (int16_t)psx_mod_read_half(actor + 0x16),
        (int16_t)psx_mod_read_half(0x1F800176u),
        (int16_t)psx_mod_read_half(0x1F800186u));
    psx_mod_write_byte(actor + 1, (uint8_t)visible);
    return 1;
}

void tomba_widescreen_scripts_activate(void) { enabled = 1; }
void tomba_widescreen_scripts_tick(void) {
    if (enabled) tomba_dispatch_install();
}

PSX_MOD_CONSTRUCTOR(tomba_register_widescreen_scripts) {
    tomba_dispatch_register(script_visibility);
}
