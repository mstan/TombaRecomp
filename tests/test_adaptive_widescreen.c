/* This is an assertion-based executable, including in Release builds. */
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "../src/mods/tomba_widescreen_hud.h"
#include "../src/mods/tomba_widescreen_residency.h"
#include "../src/mods/tomba_widescreen_sprites.h"
#include "../src/mods/tomba_widescreen_view.h"
#include "../src/mods/tomba_widescreen_scripts.h"
#include "ws_primitive_roles.h"
#include "ws_scene_latch.h"
#include "ws_backdrop_margin.h"
#include "ws_backdrop_detect.h"

/* This fixture uses main RAM packets and allocates no enhancement aperture. */
uint32_t psx_gpu_packet_key(uint32_t address) {
    return psx_gpu_packet_key_for(address, 0);
}

static TombaPoolObject pool_object(int pool, int type, int variant, int group,
                                   int x, int y, int z, int pending) {
    TombaPoolObject o;
    memset(&o, 0, sizeof o);
    o.pool = (uint8_t)pool; o.type = (uint8_t)type; o.variant = (uint8_t)variant;
    o.group = (int8_t)group; o.pending = (uint8_t)pending;
    o.x = (int32_t)((uint32_t)(uint16_t)x << 16);
    o.y = (int32_t)((uint32_t)(uint16_t)y << 16);
    o.z = (int32_t)((uint32_t)(uint16_t)z << 16);
    o.owner = -1;
    return o;
}

static void check_bank_owners(void) {
    /* beads-eio.4.27: area 1 sector 1, bank 0 already retired. The elders'
     * message bubble (80030800: pool 0, type 1A, variant 0, pool-clear group 0)
     * must not make bank 0 look resident, and must not be owned/retired. */
    const TombaBankRecord records[] = {
        /* pool type var grp rel   x     y    z */
        {0, 0x15, 3, 0, 0, 3135, -250, 35},   /* bank 0 scenery */
        {0, 0x1A, 9, 0, 0,  930, -167, 35},   /* bank 0 sign, type shared w/ bubble */
        {0, 0x05, 1, 0, 0, 2000, -300, 0},    /* bank 0 actor (moves) */
        {0, 0x18, 2, 0, 1,   16,    0, 0},    /* bank 0 chained to its parent */
        {0, 0x19, 7, 1, 0, 3729, -623, 0},    /* bank 1 scenery */
        {0, 0x1A, 0x63, 1, 0, 4242, -394, 35}, /* bank 1 exit arrow */
        {2, 0x04, 0, 0, 0, 2500, -200, 0},    /* bank 0, third pool */
        {0, 0x15, 3, -1, 0, 2709, -227, 0},   /* shared: owned by no bank */
    };
    const unsigned nrec = sizeof records / sizeof *records;
    TombaPoolObject o[8];
    unsigned n = 0;
    o[n++] = pool_object(0, 0x19, 7, 1, 3729, -623, 0, 0);
    o[n++] = pool_object(0, 0x1A, 0x63, 1, 4242, -394, 35, 0);
    o[n++] = pool_object(0, 0x1A, 0, 0, 141, 167, 0, 0); /* bubble */
    o[n++] = pool_object(0, 0x05, 9, 0, 0, 0, 0, 0);     /* effect, group 0 */
    assert(tomba_assign_bank_owners(records, nrec, 0, o, n) == 0);
    assert(tomba_assign_bank_owners(records, nrec, 1, o, n) == 2);
    assert(o[0].owner == 1 && o[0].anchored && o[1].owner == 1 && o[1].anchored);
    assert(o[2].owner == -1 && o[3].owner == -1);
    assert(!tomba_roof_keep_group(0, 2)); /* group alone WOULD retire the bubble */

    /* Both banks resident: every bank-0 object is owned exactly once. A
     * moved actor is owned by signature but does not anchor; a chained record
     * never anchors. A second object with the same signature as a record that
     * is already owned stays unowned (1:1). */
    n = 0;
    o[n++] = pool_object(0, 0x15, 3, 0, 3135, -250, 35, 0);
    o[n++] = pool_object(0, 0x05, 1, 0, 2112, -301, 0, 0);  /* moved actor */
    o[n++] = pool_object(0, 0x18, 2, 0, 16, 0, 0, 0);       /* chained: abs pos differs */
    o[n++] = pool_object(0, 0x1A, 9, 0, 930, -167, 35, 0);
    o[n++] = pool_object(0, 0x1A, 9, 0, 930, -167, 35, 0);  /* duplicate signature */
    o[n++] = pool_object(2, 0x04, 0, 0, 2500, -200, 0, 0);
    o[n++] = pool_object(1, 0x15, 3, 0, 3135, -250, 35, 0); /* wrong pool */
    assert(tomba_assign_bank_owners(records, nrec, 0, o, n) == 3);
    assert(o[0].owner == 0 && o[0].anchored);
    assert(o[1].owner == 0 && !o[1].anchored);
    assert(o[2].owner == 0 && !o[2].anchored);
    assert(o[3].owner == 0 && o[3].anchored && o[4].owner == -1);
    assert(o[5].owner == 0 && o[5].anchored && o[6].owner == -1);

    /* A record's anchor is preferred over a signature-only claim, whatever the
     * pool order, and destruction-pending anchors do not prove residency. */
    n = 0;
    o[n++] = pool_object(0, 0x15, 3, 0, 3000, -250, 35, 0); /* same sig, moved */
    o[n++] = pool_object(0, 0x15, 3, 0, 3135, -250, 35, 1); /* anchor, pending */
    assert(tomba_assign_bank_owners(records, nrec, 0, o, n) == 0);
    assert(o[1].owner == 0 && o[1].anchored && o[0].owner == -1);

    /* Exact 16.16 position: a fractional offset is not the spawn point. */
    n = 0;
    o[n] = pool_object(0, 0x15, 3, 0, 3135, -250, 35, 0);
    o[n++].x += 1;
    assert(tomba_assign_bank_owners(records, nrec, 0, o, n) == 0);
    assert(o[0].owner == 0 && !o[0].anchored);
}

static void check_detector(void) {
    /* Shared magic is established in the taken branch's delay slot. The
     * skipped arm clobbers it; a linear nearest-definition scan is wrong. */
    const uint32_t branch_magic[] = {
        0x15000004, 0x3C026666, 0x2402007B, 0x08000040, 0,
        0x3C031F80, 0x84630176, 0x34426667
    };
    uint32_t magic = 0;
    assert(psx_ws_bd_constant(branch_magic, 8, 0, 2, 4, &magic));
    assert(magic == 0x66666667u);
    /* Bridge: first strip is [q,q+17], second is [q+33,q+44].
     * The second divide reuses camera a0 and magic a1 across the first clamp.
     * Its width is 11, NOT the absolute end-table offset 44. */
    uint32_t bridge[] = {
        0x3C056666, 0x3C041F80, 0x84840176, 0x34A56667, 0x2483FF88,
        0x00650018, 0x00031FC3, 0x00003010, 0x00061143, 0x00431023,
        0x00409021, 0x24430011, 0x00021400, 0x04410002, 0x00608821,
        0x00009021, 0x00031400, 0x00021403, 0x28420021, 0x14400002,
        0x2482FFB0, 0x24110020, 0x00450018, 0x000217C3, 0x00003010,
        0x00061943, 0x00621823, 0x24620021, 0x00402821, 0x2464002C,
        0x00021400, 0x00021403, 0x28420021, 0x10400002, 0x00801821,
        0x24050021, 0x00041400, 0x00021403, 0x2842003F, 0x14400002,
        0x00A02021, 0x2403003E
    };
    WsBackdropSite bridge_sites[8];
    int bn = psx_ws_find_backdrop_windows(bridge, 42, 0x80116978, bridge_sites, 8);
    assert(bn == 4);
    assert(bridge_sites[0].pc == 0x801169A0 && bridge_sites[0].window_cols == 17);
    assert(bridge_sites[2].pc == 0x801169E4 && bridge_sites[2].kind == WS_BD_START);
    assert(bridge_sites[3].pc == 0x801169EC && bridge_sites[3].kind == WS_BD_END);
    assert(bridge_sites[2].window_cols == 11 && bridge_sites[3].window_cols == 11);
    bridge[1] = 0x3C048000; /* same offset in unrelated memory is not camera X */
    assert(psx_ws_find_backdrop_windows(bridge, 42, 0x80116978, bridge_sites, 8) == 0);
    bridge[1] = 0x3C041F80;
    bridge[2] = 0x24040299; /* overwritten camera provenance must not survive */
    assert(psx_ws_find_backdrop_windows(bridge, 42, 0x80116978, bridge_sites, 8) == 0);

    uint32_t biased[] = {
        0x3C036666, 0x3C021F80, 0x84420176, 0x34636667, 0x2442FF24,
        0x00430018, 0x000217C3, 0x00003010, 0x00061943, 0x00621823,
        0x2462003F, 0x00402821, 0x24640046
    };
    bn = psx_ws_find_backdrop_windows(biased, 13, 0x80116C08, bridge_sites, 8);
    assert(bn == 2 && bridge_sites[0].window_cols == 7);
    assert(bridge_sites[0].pc == 0x80116C30 && bridge_sites[1].pc == 0x80116C38);
    biased[12] = 0x24440046; /* dependent on already-shifted first bound: reject */
    assert(psx_ws_find_backdrop_windows(biased, 13, 0x80116C08, bridge_sites, 8) == 0);
    biased[12] = 0x24630046; /* last consumer may overwrite the old quotient */
    assert(psx_ws_find_backdrop_windows(biased, 13, 0x80116C08, bridge_sites, 8) == 2);
    biased[10] = 0x24620046; biased[12] = 0x2464003F; /* either order */
    bn = psx_ws_find_backdrop_windows(biased, 13, 0x80116C08, bridge_sites, 8);
    assert(bn == 2 && bridge_sites[0].kind == WS_BD_END);
    assert(bridge_sites[1].kind == WS_BD_START && bridge_sites[1].window_cols == 7);

    /* Tower scene: /80, independent bounds, END in the jump delay slot. */
    uint32_t code[] = {
        0x3C026666, 0x3C031F80, 0x84630176, 0x34426667,
        0x2463F9CA, 0x00620018, 0x00031FC3, 0x00003010,
        0x00061143, 0x00431023, 0x00409021, 0x08045B9B, 0x24510009
    };
    WsBackdropSite sites[8];
    int n = psx_ws_find_backdrop_windows(code, 13, 0x80116DFC, sites, 8);
    assert(n == 2 && sites[0].kind == WS_BD_START && sites[1].kind == WS_BD_END);
    assert(sites[0].pc == 0x80116E24 && sites[1].pc == 0x80116E2C);
    assert(sites[0].window_cols == 9 && sites[1].window_cols == 9);
    code[12] = 0x26510009; /* dependent s1 = shifted s2 + 9: not safe */
    assert(psx_ws_find_backdrop_windows(code, 13, 0x80116DFC, sites, 8) == 0);
    /* Actual false positive at 80116638: layer bias after a quotient clamp. */
    const uint32_t layer[] = {
        0x3C026666, 0x3C031F80, 0x84630176, 0x34426667,
        0x2463FC54, 0x00620018, 0x00031FC3, 0x00003810,
        0x00071143, 0x00431023, 0x00402021, 0x00021400,
        0x04410003, 0x2482001C
    };
    assert(psx_ws_find_backdrop_windows(layer, 14, 0x80116610, sites, 8) == 0);
    uint32_t segmented[19];
    memcpy(segmented, layer, sizeof layer);
    segmented[14] = 0x00002021; segmented[15] = 0x2482001C;
    segmented[16] = 0x00402021; segmented[17] = 0x080459AC;
    segmented[18] = 0x24430008;
    n = psx_ws_find_backdrop_windows(segmented, 19, 0x80116610, sites, 8);
    assert(n == 2 && sites[0].pc == 0x80116650 && sites[1].pc == 0x80116658);
    assert(sites[0].window_cols == 8 && sites[1].window_cols == 8);
    segmented[15] ^= 1; /* inconsistent bias: reject the whole ambiguous shape */
    assert(psx_ws_find_backdrop_windows(segmented, 19, 0x80116610, sites, 8) == 0);
    code[11] = 0; code[12] = 0x2451FFEE; /* independent negative START */
    n = psx_ws_find_backdrop_windows(code, 13, 0x80116DFC, sites, 8);
    assert(n == 2 && sites[0].kind == WS_BD_END && sites[1].kind == WS_BD_START);
    assert(sites[1].window_cols == 18);
}

static uint32_t stack[64];
static uint32_t read_stack(uint32_t addr) {
    assert(addr >= 0x1000 && addr < 0x1100 && !(addr & 3));
    return stack[(addr - 0x1000) / 4];
}
static void check_hud(uint32_t ra, unsigned offset, uint32_t parent,
                       unsigned root_offset, uint32_t root, int edge) {
    memset(stack, 0, sizeof stack);
    stack[offset / 4] = parent;
    if (root_offset) stack[root_offset / 4] = root;
    assert(tomba_hud_edge(ra, 0x1000, read_stack) == edge);
    /* Same shared builder outside the persistent HUD must not move. */
    stack[(root_offset ? root_offset : offset) / 4] = 0x80123456;
    assert(tomba_hud_edge(ra, 0x1000, read_stack) == 0);
}
int main(void) {
    const char* values[] = {"16:9", "21:9", "32:9", "Fit", "", NULL};
    const unsigned numerators[] = {16, 21, 32, 16, 16, 16};
    for (unsigned i = 0; i < sizeof values / sizeof values[0]; ++i) {
        TombaWidescreenView view = tomba_widescreen_view(values[i]);
        assert(view.numerator == numerators[i] && view.denominator == 9);
        assert(view.fit == (i >= 3));
    }
    WsSceneLatch scene = {0};
    /* Room effects can project thousands of vertices, but cannot promote 2D. */
    for (uint32_t f = 0; f < 100; ++f)
        assert(ws_scene_is_2d(&scene, f, 0, 1, 6));
    assert(!ws_scene_is_2d(&scene, 100, 1, 1, 6));
    /* The observed outdoor cadence has 6-8 vblank gaps between GP0 bursts.
     * Active GTE work holds the confirmed world across them, at any duration. */
    for (uint32_t f = 101; f < 1301; ++f)
        assert(!ws_scene_is_2d(&scene, f, f % 9 == 0, 1, 6));
    for (uint32_t f = 1301; f <= 1306; ++f)
        assert(!ws_scene_is_2d(&scene, f, 0, 0, 6));
    assert(ws_scene_is_2d(&scene, 1307, 0, 0, 6));
    for (uint32_t f = 1308; f < 1400; ++f)
        assert(ws_scene_is_2d(&scene, f, 0, 1, 6)); /* jingle cannot reenter */
    assert(!ws_scene_is_2d(&scene, 1400, 1, 1, 6));
    assert(ws_scene_is_2d(&scene, 10, 0, 1, 6)); /* rewind forgets proof */
    assert(!ws_scene_is_2d(&scene, 0xFFFFFFFEu, 1, 1, 6));
    assert(!ws_scene_is_2d(&scene, 0xFFFFFFFFu, 0, 1, 6));
    assert(!ws_scene_is_2d(&scene, 0, 0, 1, 6)); /* natural clock wrap */
    assert(tomba_is_world_sprite(0x8004A170));
    assert(!tomba_is_world_sprite(0x8004E830)); /* AP */
    assert(!tomba_is_world_sprite(0x8004F450)); /* shared HUD/dialogue */
    assert(!tomba_is_world_sprite(0x801217B4)); /* overlay backdrop */
    static WsPrimitiveRole roles[WS_ROLE_BUCKETS];
    WsPrimitiveRole* role = ws_role_write(roles, 0x800B3638, 10);
    assert(role);
    role->world = 1;
    ws_role_write(roles, 0x000B3638, 10)->hud_edge = -1;
    const WsPrimitiveRole* found = ws_role_read(roles, 0x000B363C, 11);
    assert(found && found->world && found->hud_edge == -1);
    assert(!ws_role_read(roles, 0x000B3638, 11)); /* P_TAG isn't GP0 word */
    assert(!ws_role_read(roles, 0xFFFFFFFFu, 11));
    assert(!ws_role_read(roles, 0x000B363C, 13)); /* expiry */
    assert(!ws_role_read(roles, 0x000B363C, 9)); /* frame rewind */
    role = ws_role_write(roles, 0x800B3638, 12); /* recycled packet */
    assert(role && !role->world && !role->hud_edge);
    role->world = 1;
    ws_role_write(roles, 0x800B3638, 12)->world = 0; /* same-frame clear */
    assert(!ws_role_read(roles, 0x000B363C, 12)->world);
    assert(!ws_role_write(roles, 0, 12));
    assert(!ws_role_read(roles, 4, 12));
    assert(tomba_roof_resident_mask(2721, 388, 0) == 3);
    assert(tomba_roof_resident_mask(2820, 388, 1) == 3);
    assert(tomba_roof_resident_mask(2721, 0, 0) == 1);
    assert(tomba_roof_resident_mask(2820, 0, 1) == 2);
    assert(tomba_roof_resident_mask(1800, 388, 0) == 1);
    assert(tomba_roof_resident_mask(3800, 388, 1) == 2);
    assert(tomba_roof_resident_mask(2721, 388, 3) == 0);
    assert(tomba_roof_keep_group(-1, 1) && tomba_roof_keep_group(-1, 2));
    assert(tomba_roof_keep_group(0, 3) && tomba_roof_keep_group(1, 3));
    assert(!tomba_roof_keep_group(1, 1) && !tomba_roof_keep_group(0, 2));
    check_detector();
    check_bank_owners();
    /* The cutscene's actor-visibility opcode uses the retail camera window
     * even when drawing extends farther. Check both inclusive edges, vertical
     * clipping and the original halfword wrap behavior. */
    assert(tomba_script_visible(936, 564, 1000, 500));
    assert(tomba_script_visible(1384, 196, 1000, 500));
    assert(!tomba_script_visible(935, 500, 1000, 500));
    assert(!tomba_script_visible(1385, 500, 1000, 500));
    assert(!tomba_script_visible(1000, 565, 1000, 500));
    assert(!tomba_script_visible(1000, 195, 1000, 500));
    assert(!tomba_script_visible(1500, 500, 1000, 500)); /* wide fringe */
    assert(tomba_script_visible(-32768, 0, 32767, 0));
    check_hud(0x8004E830, 0x2c, 0x8004E4D4, 0, 0, 1);
    check_hud(0x8004E9AC, 0x3c, 0x8004E4E8, 0, 0, -1);
    check_hud(0x8004EEF4, 0x20, 0x8004E4F8, 0, 0, -1);
    check_hud(0x8004F330, 0x20, 0x8004E7AC, 0x54, 0x8004E4D4, 1);
    const uint32_t lives[] = {0x8004E62C, 0x8004E6B8, 0x8004E6DC};
    for (unsigned i = 0; i < sizeof lives / sizeof *lives; ++i)
        check_hud(0x8004F330, 0x20, lives[i], 0x54, 0x8004E4C4, -1);
    check_hud(0x8004F450, 0x28, 0x8004EAD0, 0x6c, 0x8004E4E8, -1);
    const uint32_t icons[] = {0x8004EDEC, 0x8004EE18, 0x8004EE44,
                              0x8004EE70, 0x8004EE9C};
    for (unsigned i = 0; i < sizeof icons / sizeof *icons; ++i)
        check_hud(0x8004F450, 0x28, icons[i], 0x50, 0x8004E4F8, -1);
    assert(tomba_hud_edge(0x80046000, 0x1000, read_stack) == 0);
    assert(psx_ws_backdrop_columns(9, 0, 320) == 0); /* 4:3 */
    assert(psx_ws_backdrop_columns(9, 85, 320) == 3); /* 16:9 + guard */
    assert(psx_ws_backdrop_columns(9, 152, 320) == 5); /* 21:9 */
    assert(psx_ws_backdrop_columns(9, 299, 320) == 9); /* 32:9 */
    assert(psx_ws_backdrop_columns(9, 388, 320) == 11); /* reported scene */
    assert(psx_ws_backdrop_columns(9, 725, 320) == 21); /* 64:9 */
    assert(psx_ws_backdrop_columns(9, 1, 320) == 1); /* round out */
    assert(psx_ws_backdrop_columns(9, 10, 0) == 0);
    assert(psx_ws_backdrop_columns(255, 0x7fffffff, 320) == 0x3fff);
    assert(psx_ws_backdrop_bound(32, 0, 11) == 21);
    assert(psx_ws_backdrop_bound(41, 1, 11) == 52);
    assert(psx_ws_backdrop_bound(28, 0, 40) == 0);
    assert(psx_ws_backdrop_bound(32000, 1, 1000) == 0x7fff);
    puts("PASS: world/HUD packet roles, rooftop residency, bank ownership and adaptive terrain bounds");
    return 0;
}
