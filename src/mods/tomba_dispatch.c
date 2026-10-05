#include "tomba_dispatch.h"
#include "bios_hle.h"

/* One chain owner for title hooks. Independently enabled mods must not wrap
 * each other's dispatchers again every VBlank and form a recursive chain. */
static TombaDispatchHook hooks[8];
static unsigned count;
static TombaDispatchHook previous;

static int dispatch(CPUState* cpu, uint32_t phys) {
    for (unsigned i = 0; i < count; ++i)
        if (hooks[i](cpu, phys)) return 1;
    return previous ? previous(cpu, phys) : 0;
}

void tomba_dispatch_register(TombaDispatchHook hook) {
    for (unsigned i = 0; i < count; ++i)
        if (hooks[i] == hook) return;
    if (hook && count < sizeof hooks / sizeof *hooks) hooks[count++] = hook;
}

void tomba_dispatch_install(void) {
    if (g_psx_bios_hle_hook != dispatch) {
        previous = g_psx_bios_hle_hook;
        g_psx_bios_hle_hook = dispatch;
    }
}
