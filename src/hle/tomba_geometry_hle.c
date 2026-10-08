/* SCUS-94236 geometry batches (80024EEC, 800251C0, 800253C8).
 * Inputs: original packed F4/GT3/GT4 records, world vertices, OT and optional
 * animated object UVs. Outputs: identical packet bytes, OT links, allocator,
 * scratch vertex cursor, GTE results, v0 next-record pointer and pc=$ra.
 * Caller-saved temporaries and stack scratch are private to this operation.
 * Native batches remove MIPS dispatch/load/stall bookkeeping, retain exact
 * shared GTE math and precision provenance, and charge a bounded batch estimate.
 * Full enhanced-renderer widescreen culling stays active; no stock reconstruction.
 * Build selection and LLE floor: TOMBA_GEOMETRY_IMPL in CMakeLists.txt.
 */
#include "cpu_state.h"
#include "gpu.h"
#include "pgxp_hooks.h"
#include "psx_cycles.h"
#include "mod_plugins.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef TOMBA_GEOMETRY_VALIDATE
#include "psx_cycle_freeze.h"
extern uint8_t* memory_get_ram_ptr(void);
extern uint8_t* memory_get_scratchpad_ptr(void);
extern uint32_t memory_get_ram_bytes(void);
extern void tomba_lle_80024EEC(CPUState*);
extern void tomba_lle_800251C0(CPUState*);
extern void tomba_lle_800253C8(CPUState*);
#endif

extern uint32_t g_debug_last_store_pc;

static void vertex(CPUState* cpu, unsigned reg, uint32_t address) {
    for (unsigned k = 0; k < 2; ++k) {
        unsigned r = reg + k;
        uint32_t v = cpu->read_word(address + k * 4);
        gte_write_data(cpu, (uint8_t)r, v);
        PGXP_COP2(0xC8000000u | (r << 16), v, address + k * 4);
    }
}

static void xy(CPUState* cpu, unsigned reg, uint32_t address, uint32_t store_pc) {
    uint32_t v = gte_read_data(cpu, (uint8_t)reg);
    g_debug_last_store_pc = store_pc;
    cpu->write_word(address, v);
    gte_precision_store_word(address, (uint8_t)reg);
    PGXP_COP2(0xE8000000u | (reg << 16), v, address);
}

static void geometry(CPUState* cpu, unsigned kind) {
    const int flat = kind == 0, quad = kind != 1;
    const unsigned stride = kind == 2 ? 52 : 40;
    const unsigned nverts = quad ? 4 : 3;
    const unsigned xy_step = flat ? 8 : 12;
    uint32_t record = cpu->gpr[flat ? 5 : 4];
    uint32_t vertices = cpu->gpr[flat ? 6 : 5];
    const uint32_t ot = cpu->gpr[flat ? 7 : 6];
    const uint32_t object = flat ? cpu->gpr[4] : 0;
    const uint32_t count = cpu->read_word(record);
    record += 4;
    const uint32_t frame = cpu->read_word(0x1F8001E0u);
    const unsigned vertex_offset = flat ? 8 : kind == 1 ? 16 : 20;
    if (count > 65535) { fprintf(stderr, "tomba geometry: invalid record count\n"); abort(); }
    uint32_t emitted = 0;
    for (uint32_t i = 0; i < count; ++i, record += stride, vertices += stride) {
        vertex(cpu, 0, vertices + vertex_offset);
        vertex(cpu, 2, vertices + vertex_offset + 8);
        vertex(cpu, 4, vertices + vertex_offset + 16);
        gte_execute(cpu, 0x0280030u);
        uint32_t flags = gte_read_ctrl(cpu, 31);
        cpu->write_word(0x1F800070u, flags);
        if ((int32_t)flags < 0) continue;
        gte_execute(cpu, 0x1400006u);
        int32_t facing = (int32_t)gte_read_data(cpu, 24);
        cpu->write_word(0x1F800070u, (uint32_t)facing);
        if (facing <= 0) continue;
        uint32_t packet = cpu->read_word(0x1F800164u);
        const uint32_t base_pc = flat ? 0x80024F88u : kind == 1 ? 0x8002525Cu : 0x80025464u;
        xy(cpu, 12, packet + 8, base_pc);
        xy(cpu, 13, packet + 8 + xy_step, base_pc + 4);
        xy(cpu, 14, packet + 8 + xy_step * 2, base_pc + 8);
        if (quad) {
            vertex(cpu, 0, vertices + vertex_offset + 24);
            gte_execute(cpu, 0x0180001u);
            flags = gte_read_ctrl(cpu, 31);
            cpu->write_word(0x1F800070u, flags);
            if ((int32_t)flags < 0) continue;
            xy(cpu, 14, packet + 8 + xy_step * 3, flat ? 0x80024FCCu : 0x800254A8u);
        }
        int visible_y = 0, visible_x = 0;
        for (unsigned j = 0; j < nverts; ++j) {
            uint32_t projected = cpu->read_word(packet + 8 + xy_step * j);
            visible_y |= (projected >> 16) < 224u;
            visible_x |= psx_ws_cull_sltiu(projected & 0xFFFFu, 320);
        }
        if (!visible_y || !visible_x) continue;
        gte_execute(cpu, quad ? 0x168002Eu : 0x158002Du);
        uint32_t bucket = ot + (gte_read_data(cpu, 7) << 2);
        const int animated = object && (cpu->read_byte(object + 28) & 15) == 8 &&
            cpu->read_byte(object + 2) == 1;
        if (flat) {
            cpu->write_word(packet + 4, cpu->read_word(record + 4));
            cpu->write_half(packet + 14, cpu->read_half(record));
            cpu->write_half(packet + 22, cpu->read_half(record + 2));
        }
        if (animated) bucket = frame + 12;
        else if ((uint32_t)(bucket - frame) >= 3232u) continue;
        if (!flat) {
            for (unsigned j = 0; j < nverts; ++j)
                cpu->write_word(packet + 4 + j * 12, cpu->read_word(record + 4 + j * 4));
            cpu->write_half(packet + 14, cpu->read_half(record));
            cpu->write_half(packet + 26, cpu->read_half(record + 2));
        }
        for (unsigned j = 0; j < nverts; ++j) {
            uint16_t uv = cpu->read_half(animated ? object + 108 + j * 2 :
                record + (stride - 2 - (nverts - 1 - j) * 8));
            cpu->write_half(packet + 12 + xy_step * j, uv);
        }
        uint32_t link = cpu->read_word(bucket);
        cpu->write_word(bucket, packet);
        cpu->write_word(packet, link | (kind == 2 ? 0x0C000000u : 0x09000000u));
        cpu->write_word(0x1F800164u, packet + stride);
        ++emitted;
    }
    cpu->write_word(0x1F80008Cu, vertices);
    cpu->gpr[2] = record;
    cpu->pc = cpu->gpr[31];
    /* The completed batch is atomic. Estimate computation, with ordinary
     * VSync/device pacing still live. Publish the continuation before servicing. */
    cpu->gte_ts_done = psx_cycle_count;
    psx_mod_counter_add("tomba.geometry.hle.batches", 1);
    psx_mod_counter_add("tomba.geometry.hle.polygons", count);
    psx_mod_counter_add("tomba.geometry.hle.emitted", emitted);
    psx_advance_cycles(16u + count * 24u);
}

static void entry(CPUState* cpu, unsigned kind) {
    if (cpu->pc) { fprintf(stderr, "tomba geometry: interior entry 0x%08X unsupported in HLE\n", cpu->pc); abort(); }
#ifdef TOMBA_GEOMETRY_VALIDATE
    /* Test binary only: run the reference on an isolated copy of the inputs.
     * The product build never dual-executes. No GPU submission occurs here. */
    static unsigned checked[3];
    static uint8_t *before, *expected;
    uint32_t bytes = memory_get_ram_bytes();
    if (checked[kind] < 200 && !g_psx_guest_time_frozen) {
        uint8_t spad_before[1024], spad_expected[1024];
        CPUState input = *cpu, reference;
        PsxCycleFreeze freeze;
        if (!before) { before = malloc(bytes); expected = malloc(bytes); }
        if (!before || !expected) abort();
        memcpy(before, memory_get_ram_ptr(), bytes);
        memcpy(spad_before, memory_get_scratchpad_ptr(), 1024);
        if (!psx_cycle_freeze_begin(&freeze, 0, NULL)) abort();
        gte_precision_speculative_begin();
        void (*original[])(CPUState*) = {tomba_lle_80024EEC, tomba_lle_800251C0, tomba_lle_800253C8};
        original[kind](cpu);
        reference = *cpu;
        memcpy(expected, memory_get_ram_ptr(), bytes);
        memcpy(spad_expected, memory_get_scratchpad_ptr(), 1024);
        memcpy(memory_get_ram_ptr(), before, bytes);
        memcpy(memory_get_scratchpad_ptr(), spad_before, 1024);
        *cpu = input;
        gte_precision_speculative_end();
        psx_cycle_freeze_end(&freeze);
        geometry(cpu, kind);
        /* Original stack scratch is not read after return. */
        uint32_t stack = (input.gpr[29] - 8) & (bytes - 1);
        memcpy(expected + stack, memory_get_ram_ptr() + stack, 8);
        int bad = cpu->gpr[2] != reference.gpr[2] || cpu->pc != reference.pc ||
            memcmp(cpu->gpr + 16, reference.gpr + 16, 16 * sizeof(uint32_t)) ||
            memcmp(cpu->gte_data, reference.gte_data, sizeof cpu->gte_data) ||
            memcmp(cpu->gte_ctrl, reference.gte_ctrl, sizeof cpu->gte_ctrl) ||
            memcmp(expected, memory_get_ram_ptr(), bytes) ||
            memcmp(spad_expected, memory_get_scratchpad_ptr(), 1024);
        if (bad) {
            unsigned delta = 0; while (delta < bytes && expected[delta] == memory_get_ram_ptr()[delta]) ++delta;
            fprintf(stderr, "tomba geometry HLE DIFFERENCE kind=%u sample=%u ram=0x%08X v0=%08X/%08X\n",
                kind, checked[kind], delta, cpu->gpr[2], reference.gpr[2]);
            for (unsigned i = 0; i < 32; ++i) if (cpu->gte_data[i] != reference.gte_data[i])
                fprintf(stderr, "GTE data[%u]=%08X/%08X\n", i, cpu->gte_data[i], reference.gte_data[i]);
            for (unsigned i = 0; i < 1024; ++i) if (spad_expected[i] != memory_get_scratchpad_ptr()[i]) {
                fprintf(stderr, "SPAD byte[%u]=%02X/%02X\n", i, memory_get_scratchpad_ptr()[i], spad_expected[i]); break;
            }
            abort();
        }
        if (++checked[kind] == 200) fprintf(stdout, "tomba geometry HLE validation: kind=%u 200 isolated batches match\n", kind);
        return;
    }
#endif
    geometry(cpu, kind);
}

void func_80024EEC(CPUState* cpu) { entry(cpu, 0); }
void func_800251C0(CPUState* cpu) { entry(cpu, 1); }
void func_800253C8(CPUState* cpu) { entry(cpu, 2); }
