#include "mod_plugins.h"
#include "cpu_state.h"
#include "tomba_widescreen_residency.h"
#include <stdio.h>
#include <string.h>

/* SCUS-94236. Reuse the game's allocator/constructor and event predicate.
 * No copied actors, synthetic pickups, modified area ID, or extra pool writes.
 * The two validated roof banks fit together in the original fixed pools. */
static int enabled;
static int last_report = -1;

typedef struct { uint32_t base, stride, free_count; unsigned count; } Pool;
static const Pool pools[] = {
    {0x800A5970u, 0xD4u, 0x1F800238u, 200},
    {0x800B0B88u, 0xD4u, 0x1F80023Au, 45},
    {0x800A3D08u, 0x6Cu, 0x1F80023Cu, 10}
};
typedef struct { uint32_t record; int event; unsigned pool; } Spawn;

void tomba_widescreen_residency_activate(void) { enabled = 1; }

static int ram_record(uint32_t p, uint32_t bytes) {
    return p >= 0x80098000u && p <= 0x80200000u - bytes;
}

/* Reconstruct residency from guest state every time. No host-only ownership
 * cache that could survive a savestate load and duplicate/miss a whole bank. */
static unsigned inspect_pools(unsigned* pending, unsigned* shared) {
    unsigned loaded = 0;
    *pending = *shared = 0;
    for (unsigned p = 0; p < 3; ++p) {
        for (unsigned i = 0; i < pools[p].count; ++i) {
            uint32_t a = pools[p].base + i * pools[p].stride;
            if (!psx_mod_read_byte(a)) continue;
            int group = (int8_t)psx_mod_read_byte(a + 0x1D);
            if (psx_mod_read_byte(a + 0x1C) & 0x80) continue;
            if (group == -1) *shared = 1;
            if (group < 0 || group > 1) continue;
            if (psx_mod_read_byte(a + 4) >= 2) *pending |= 1u << group;
            else loaded |= 1u << group;
        }
    }
    return loaded;
}

static int event_available(CPUState* cpu, unsigned event) {
    CPUState saved = *cpu;
    cpu->gpr[4] = event;
    /* Generated functions are CPS fragments, not synchronous C callees.
     * Use the nested dispatch contract with the real loader's post-call PC. */
    cpu->gpr[31] = 0x8005A5F8u;
    psx_dispatch_call(cpu, 0x80023608u, cpu->gpr[31]);
    int available = cpu->gpr[2] == 0;
    *cpu = saved;
    return available;
}

static int collect(CPUState* cpu, uint32_t list, unsigned sector, int events,
                   unsigned shared, Spawn* plan, unsigned* count) {
    if (!ram_record(list, 16)) return 0;
    for (unsigned i = 0; i < 512; ++i, list += 16) {
        if (!ram_record(list, 16)) return 0;
        if (psx_mod_read_byte(list + 2) == 0xFF) return 1;
        int group = (int8_t)psx_mod_read_byte(list);
        int event = -1;
        if (events) {
            if (group != (int)sector && group != ~(int)sector) continue;
            event = psx_mod_read_byte(list + 15) >> 2;
            if (!event_available(cpu, (unsigned)event)) continue;
        }
        if (group == -1 && shared) continue;
        /* Fail closed on another bank's records or unsupported allocator kind. */
        if (group != (int)sector && group != -1) return 0;
        unsigned kind = psx_mod_read_byte(list + 1) & 0x7F;
        unsigned pool;
        if (kind >= 2 && kind <= 5) pool = 0;
        else if (kind == 8) pool = 1;
        else if (kind == 7) pool = 2;
        else return 0;
        if (*count >= 512) return 0;
        plan[(*count)++] = (Spawn){list, event, pool};
    }
    return 0; /* missing terminator */
}

static int add_bank(CPUState* cpu, unsigned sector, unsigned shared) {
    uint32_t table = psx_mod_read_word(0x8007F0CCu); /* area 1's bank table */
    if (table != 0x8007EEFCu) return 0;
    uint32_t slot = psx_mod_read_word(table + sector * 4);
    if (slot != 0x1F800358u + sector * 4) return 0;
    Spawn plan[512];
    unsigned count = 0, need[3] = {0, 0, 0};
    if (!collect(cpu, psx_mod_read_word(slot), sector, 0, shared, plan, &count)) return 0;
    unsigned event_bank = psx_mod_read_half(0x8007B296u);
    if (event_bank > 15) event_bank = 15;
    uint32_t event_slot = psx_mod_read_word(table + event_bank * 4);
    if (event_slot < 0x1F800000u || event_slot > 0x1F8003FCu) return 0;
    if (!collect(cpu, psx_mod_read_word(event_slot), sector, 1, shared, plan, &count)) return 0;
    for (unsigned i = 0; i < count; ++i) ++need[plan[i].pool];
    /* All-or-nothing preflight, with spare primary slots for gameplay spawns.
     * Never overrun a fixed guest arena or leave a partially loaded bank. */
    for (unsigned p = 0; p < 3; ++p) {
        int free_slots = (int16_t)psx_mod_read_half(pools[p].free_count);
        if ((int)need[p] + (p == 0 ? 8 : 0) > free_slots) return 0;
    }
    CPUState saved = *cpu;
    for (unsigned i = 0; i < count; ++i) {
        *cpu = saved;
        cpu->gpr[4] = plan[i].record;
        cpu->gpr[5] = (uint32_t)plan[i].event;
        cpu->gpr[31] = 0x8005A564u;
        psx_dispatch_call(cpu, 0x8005AA98u, cpu->gpr[31]);
    }
    *cpu = saved;
    fprintf(stdout, "tomba widescreen: resident roof bank %u, added %u objects (%u/%u/%u)\n",
            sector, count, need[0], need[1], need[2]);
    return 1;
}

static void retire_outside(unsigned mask) {
    for (unsigned p = 0; p < 3; ++p) {
        for (unsigned i = 0; i < pools[p].count; ++i) {
            uint32_t a = pools[p].base + i * pools[p].stride;
            if (!psx_mod_read_byte(a) || (psx_mod_read_byte(a + 0x1C) & 0x80)) continue;
            int group = (int8_t)psx_mod_read_byte(a + 0x1D);
            if (tomba_roof_keep_group(group, mask) || psx_mod_read_byte(a + 4) >= 2) continue;
            /* Same orderly destruction request as stock 8005A3B0. */
            psx_mod_write_byte(a, 2);
            psx_mod_write_byte(a + 4, 3);
        }
    }
}

static void residency_tick(CPUState* cpu, uint32_t address) {
    (void)address;
    if (!enabled || psx_mod_read_half(0x8009BCC8u) != 1) return;
    unsigned sector = psx_mod_read_half(0x8009BCCAu);
    if (sector > 1) return;
    /* Overlay addresses are reused. Validate the actual seam's instructions. */
    if (psx_mod_read_word(0x80115E2Cu) != 0x28420B6Eu ||
        psx_mod_read_word(0x80115F14u) != 0x28620B6Du) return;
    uint32_t manager = cpu->gpr[4];
    if (psx_mod_read_byte(manager + 4) != 1 || psx_mod_read_byte(manager + 5)) return;
    int margin = psx_mod_widescreen_x_margin();
    int camera = (int16_t)psx_mod_read_half(0x1F800176u);
    unsigned wanted = tomba_roof_resident_mask(camera, margin, sector);
    unsigned pending, shared;
    unsigned loaded = inspect_pools(&pending, &shared);
    if (wanted == 3) {
        if (pending) return; /* let an already-requested native destruction finish */
        for (unsigned bank = 0; bank < 2; ++bank) {
            if (!(loaded & (1u << bank))) {
                if (!add_bank(cpu, bank, shared)) return;
                loaded = inspect_pools(&pending, &shared);
            }
        }
    }
    if (!(loaded & (1u << sector))) return; /* native loader still owns setup */
    if (wanted != 3 && loaded == (1u << sector)) return; /* stock behavior */
    retire_outside(wanted);
    /* Synchronize the manager's observed sector, not the logical area global.
     * Its stock delta test then leaves the already-resident banks alone. */
    psx_mod_write_byte(manager + 0xE, (uint8_t)sector);
    psx_mod_write_byte(manager + 0xF, 0);
    if (last_report != (int)wanted) {
        fprintf(stdout, "tomba widescreen: roof residency mask=%u, logical=%u, camera=%d, margin=%d\n",
                wanted, sector, camera, margin);
        last_report = (int)wanted;
    }
}

PSX_MOD_CONSTRUCTOR(tomba_register_widescreen_residency) {
    (void)psx_mod_register_function_entry_plugin(
        "tomba.widescreen.residency", 0x8005A184u, residency_tick);
}
