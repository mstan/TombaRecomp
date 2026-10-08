#ifndef TOMBA_WIDESCREEN_RESIDENCY_H
#define TOMBA_WIDESCREEN_RESIDENCY_H
#include <stdint.h>

/* Area 1's roof transition is player-X 2925/2926 (overlay 80115E2C/15F14).
 * Its object banks are spatial neighbors, not alternate versions of one room.
 * Camera X is the native 320-pixel view's left edge. Include the cull guard. */
static inline unsigned tomba_roof_resident_mask(int camera_x, int margin,
                                                unsigned logical_sector) {
    if (logical_sector > 1) return 0;
    unsigned mask = 1u << logical_sector;
    if (margin > 0 && (int64_t)camera_x - margin <= 2926 &&
        (int64_t)camera_x + 320 + margin >= 2925) mask = 3;
    return mask;
}

static inline int tomba_roof_keep_group(int group, unsigned mask) {
    /* -1 is shared by banks 0 and 1. Other groups are not owned by this rule. */
    if (group < 0 || group > 1) return 1;
    return (mask & (1u << group)) != 0;
}

/*
 * Bank ownership.
 *
 * Object byte +1D (group) alone does not identify a bank object. The stock
 * constructor 8005AA98 copies the spawn record's group into +1D, but objects
 * from the dynamic allocators (8001xxxx: message bubbles at 80030800, effects,
 * drops) never write +1D and keep the pool-clear value 0. The stock game does
 * not need the distinction: its sector change (8005A3B0) retires every
 * non-shared object at one moment. With two banks resident, a group-0 bubble in
 * sector 1 looked like bank 0, so the residency rule retired it on spawn and
 * the elders' cutscene waited forever for its message (beads-eio.4.27).
 *
 * Ownership is therefore derived from the bank's spawn records, using the
 * fields the constructor copies and nothing later rewrites: pool (allocator
 * class from record byte 1), type (+2 = rec[2]), variant (+3 = rec[4]) and
 * group (+1D = rec[0]). Each record owns at most one live object. A record
 * spawned at an absolute position (rec[15]&3 is 0 or 1) is an anchor when its
 * object still holds the exact 16.16 spawn position (+10/+14/+18 =
 * rec[6/8/A] << 16). Only an anchor proves that a bank is resident: dynamic
 * objects never sit exactly on a record's spawn point with its signature, and
 * static scenery always does. Signature-only owners (moved actors, records
 * chained to a previous object) are retired with their bank but never make a
 * bank look resident.
 */
#define TOMBA_BANK_RECORDS_MAX 1024u /* base list + event list, 512 each */

typedef struct {
    uint8_t pool, type, variant;
    int8_t  group;
    uint8_t relative;      /* rec[15]&3 in {2,3}: position chained to a parent */
    int16_t x, y, z;       /* rec[6], rec[8], rec[0xA] */
} TombaBankRecord;

typedef struct {
    uint8_t pool, type, variant;
    int8_t  group;
    uint8_t pending;       /* +4 >= 2: destruction already requested */
    int32_t x, y, z;       /* raw 16.16 words +10/+14/+18 */
    /* Outputs of tomba_assign_bank_owners. */
    int8_t  owner;         /* bank index, or -1 when no record owns it */
    uint8_t anchored;      /* owner record matched at its exact spawn point */
} TombaPoolObject;

static inline int tomba_bank_signature(const TombaBankRecord* r,
                                       const TombaPoolObject* o) {
    return r->pool == o->pool && r->type == o->type &&
           r->variant == o->variant && r->group == o->group;
}

static inline int tomba_bank_anchor(const TombaBankRecord* r,
                                    const TombaPoolObject* o) {
    return !r->relative && tomba_bank_signature(r, o) &&
           o->x == (int32_t)((uint32_t)(uint16_t)r->x << 16) &&
           o->y == (int32_t)((uint32_t)(uint16_t)r->y << 16) &&
           o->z == (int32_t)((uint32_t)(uint16_t)r->z << 16);
}

/* Give each of bank's records at most one unowned object: exact anchors first,
 * then signature-only matches. Objects must start with owner = -1. Returns the
 * number of anchored, non-pending owners (bank resident iff nonzero). */
static inline unsigned tomba_assign_bank_owners(const TombaBankRecord* records,
                                                unsigned record_count, int bank,
                                                TombaPoolObject* objects,
                                                unsigned object_count) {
    unsigned anchors = 0;
    unsigned char taken[TOMBA_BANK_RECORDS_MAX];
    if (record_count > sizeof taken) record_count = sizeof taken;
    for (unsigned r = 0; r < record_count; ++r) taken[r] = 0;
    for (unsigned r = 0; r < record_count; ++r) {
        if (records[r].group != bank) continue;
        for (unsigned o = 0; o < object_count; ++o) {
            if (objects[o].owner >= 0 || !tomba_bank_anchor(&records[r], &objects[o]))
                continue;
            objects[o].owner = (int8_t)bank;
            objects[o].anchored = 1;
            taken[r] = 1;
            if (!objects[o].pending) ++anchors;
            break;
        }
    }
    for (unsigned r = 0; r < record_count; ++r) {
        if (taken[r] || records[r].group != bank) continue;
        for (unsigned o = 0; o < object_count; ++o) {
            if (objects[o].owner >= 0 || !tomba_bank_signature(&records[r], &objects[o]))
                continue;
            objects[o].owner = (int8_t)bank;
            objects[o].anchored = 0;
            break;
        }
    }
    return anchors;
}
#endif
