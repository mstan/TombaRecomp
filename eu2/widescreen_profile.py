"""Bind shared widescreen policies to reviewed SCES-01331 MAIN/area code.

Every language uses its own original instruction/data map. Only project source
and address/hash metadata are emitted. An explicit --reference-disc performs
static analysis of matching images; it does not qualify that disc's boot.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'eu2'))
LANGUAGES = {'en': 0, 'es': 5, 'pt': 6, 'sv': 7, 'da': 8}
from revisions import source as revision_source, PROFILES, active, stage_mods
CODE_KEYS = {
    0x80022c34,0x80022d68,0x80022e44,0x80022e78,0x80022e80,
    0x80022f94,0x80022f9c,0x80022fe8,0x80022ff0,0x80023068,
    0x80023070,0x800230fc,0x80023608,0x8002a1e4,0x8002cef8,
    0x8003d8b8,0x8003e828,0x8004a170,0x8004e4c4,0x8004e4d4,
    0x8004e4e8,0x8004e4f8,0x8004e62c,0x8004e6b8,0x8004e6dc,
    0x8004e7ac,0x8004e830,0x8004e9ac,0x8004ead0,0x8004edec,
    0x8004ee18,0x8004ee44,0x8004ee70,0x8004ee9c,0x8004eef4,
    0x8004f330,0x8004f450,0x8005a184,0x8005a564,0x8005a5f8,
    0x8005aa98,0x8005e08c,0x800636a4,
}


def generate(reference_disc=None, revision=None):
    if reference_disc is not None and revision is None: revision='original'
    sys.path.insert(0, str(ROOT/'psxrecomp/tools'))
    from aot_overlay_pipeline import Disc, check_disc
    disc = Disc(reference_disc or ROOT/'disc/eu2/disc.cue')
    if reference_disc is None:
        check_disc(dict(disc_hashes={'sha1':PROFILES[active()]['sha1']}),
                   disc, ROOT/'disc/eu2/disc.cue')
    contract = json.loads((revision_source('widescreen-contract.json', revision)).read_text(encoding='utf-8'))
    rows = contract['languages']
    if [r['language'] for r in rows] != list(LANGUAGES):
        raise ValueError('Unreviewed language order')
    mappings = [{int(k,16):int(v,16) for k,v in r['mapping'].items()} for r in rows]
    if any(set(row) != set(mappings[0]) for row in mappings):
        raise ValueError('Incomplete regional mapping')
    if not CODE_KEYS <= set(mappings[0]):
        raise ValueError('Incomplete original code correspondence')
    for row in rows:
        raw = disc.read(row['main'])
        if hashlib.sha256(raw).hexdigest() != row['main_sha256']:
            raise ValueError('Unreviewed original MAIN: '+row['language'])
        base = struct.unpack_from('<I',raw,24)[0]
        body = raw[2048:]
        offset = int(row['identity_address'],16)-base
        if body[offset:offset+64].hex() != row['identity']:
            raise ValueError('Original identity contract changed')
        for pc,digest in row['checks'].items():
            at = int(pc,16)-base
            if hashlib.sha256(body[at-16:at+16]).hexdigest() != digest:
                raise ValueError('MAIN instruction contract changed: '+pc)
        for area in row['overlays'].values():
            raw = disc.read(area['file'])
            if hashlib.sha256(raw).hexdigest() != area['sha256']:
                raise ValueError('Original area overlay changed: '+area['file'])
            for pc,digest in area['checks'].items():
                at = int(pc,16)-int(area['base'],16)
                if hashlib.sha256(raw[at-16:at+16]).hexdigest() != digest:
                    raise ValueError('Area instruction contract changed: '+pc)

    if reference_disc is None: stage_mods()
    out = ROOT/'build-eu2-seamless/generated/widescreen'
    out.mkdir(parents=True,exist_ok=True)
    header = '''/* Generated SCES-01331 adapter; every callback checks original state. */
#pragma once
#include "mod_plugins.h"
#include "cpu_state.h"
#include <stdint.h>
int eu_ws_refresh(void);
uint32_t eu_ws_address(uint32_t);
uint32_t eu_ws_code_key(uint32_t);
void eu_ws_register_entry(const char*, uint32_t, void (*)(CPUState*,uint32_t));
static inline uint32_t eu_ws_jal(uint32_t key) {
    return 0x0c000000u | ((eu_ws_address(key) & 0x0fffffffu) >> 2);
}
'''
    (out/'eu_widescreen.h').write_text(header,encoding='utf-8')
    keys = sorted(mappings[0])
    impl = ['#include "eu_widescreen.h"','static int language = -1;',
            'static const uint32_t keys[] = {'+','.join(hex(k)+'u' for k in keys)+'};',
            'static const uint32_t addresses[5]['+str(len(keys))+'] = {']
    for row in mappings:
        impl.append('{'+','.join(hex(row[k])+'u' for k in keys)+'},')
    impl += ['};','static const uint32_t identities[5][16] = {']
    for row in rows:
        impl.append('{'+','.join(hex(w)+'u' for w in struct.unpack('<16I',bytes.fromhex(row['identity'])))+'},')
    impl += ['};','int eu_ws_refresh(void) {','language=-1;',
        'if (!psx_mod_game_started()) return 0;',
        'for (unsigned i=0;i<5;i++) { unsigned n;',
        'const uint32_t identity_address[5] = {'+','.join(r['identity_address']+'u' for r in rows)+'};',
        'for(n=0;n<16;n++) if(psx_mod_read_word(identity_address[i]+n*4)!=identities[i][n]) break;',
        'if(n==16) { language=(int)i; return 1; } } return 0; }',
        'uint32_t eu_ws_address(uint32_t key) {',
        'if(language<0) return 0;',
        'for(unsigned k=0;k<sizeof keys/sizeof *keys;k++) if(keys[k]==key) return addresses[language][k];',
        'return 0; }',
        'uint32_t eu_ws_code_key(uint32_t address) {',
        'if(language<0) return 0;']
    # Normalize only original return-site keys, never arbitrary guest data.
    for key in sorted(CODE_KEYS):
        k=keys.index(key)
        impl.append(f'if(address==addresses[language][{k}]) return 0x{key:08x}u;')
    impl += ['return 0; }',
        'void eu_ws_register_entry(const char* id,uint32_t key,void (*callback)(CPUState*,uint32_t)) {',
        'for(unsigned k=0;k<sizeof keys/sizeof *keys;k++) if(keys[k]==key) {',
        'for(unsigned i=0;i<5;i++) { unsigned j;',
        'for(j=0;j<i;j++) if(addresses[j][k]==addresses[i][k]) break;',
        'if(j==i) (void)psx_mod_register_function_entry_plugin(id,addresses[i][k],callback);',
        '} return; } }']
    (out/'eu_widescreen.c').write_text('\n'.join(impl)+'\n',encoding='utf-8')

    for name,digest in contract['source_policy_sha256'].items():
        source = (ROOT/'src/mods'/name).read_text(encoding='utf-8')
        if hashlib.sha256(source.encode()).hexdigest()!=digest:
            raise ValueError('Review EU2 binding after shared policy changes: '+name)
        if name=='tomba_widescreen_scene.h':
            pass
        elif name=='tomba_widescreen_hud.h':
            # Keep compile-time switch keys in the shared policy's address space.
            source=source.replace('    uint32_t caller;', '    ra = eu_ws_code_key(ra);\n    uint32_t caller;')
            source=re.sub(r'(?<!\*)read_word\((sp[^)]*)\)',r'eu_ws_code_key(read_word(\1))',source)
        elif name=='tomba_widescreen_sprites.h':
            source=source.replace('return shade_tex_return ==', 'return eu_ws_code_key(shade_tex_return) ==')
        else:
            # Register every distinct regional entry before MAIN is loaded.
            # Each callback admits only the currently identified language entry.
            mark=source.find('PSX_MOD_CONSTRUCTOR')
            constructor=source[mark:] if mark>=0 else ''
            source=source[:mark] if mark>=0 else source
            constructor=constructor.replace('psx_mod_register_function_entry_plugin(', 'eu_ws_register_entry(')
            pool=re.search(r'static const Pool pools\[\] = \{.*?\n\};',source,re.S)
            descriptor=pool.group(0) if pool else None
            if descriptor:source=source.replace(descriptor,'/* POOL_DESCRIPTORS */')
            def translate(match):
                key=int(match.group(1),16)
                if key in mappings[0]:return f'eu_ws_address(0x{key:08x}u)'
                if key in (0x8000fe00,0x80098000,0x801fffb8,0x801ffffc,0x80200000):return match.group(0)
                raise ValueError(f'Unmapped guest address {match.group(0)} in {name}')
            source=re.sub(r'0x(80[0-9a-fA-F]{6})u\b',translate,source)
            source=source.replace('0x0C00B3BEu','eu_ws_jal(0x8002cef8u)')
            source=source.replace('0x0C008B91u','eu_ws_jal(0x80022e44u)')
            source=source.replace('phys != 0x22E44u', 'phys != (eu_ws_address(0x80022e44u)&0x1fffffffu)')
            if descriptor:
                source=source.replace('/* POOL_DESCRIPTORS */',descriptor)
                source=source.replace('pools[p].base','eu_ws_address(pools[p].base)')
            source=source.replace('if (!tomba_widescreen_enabled) return 0;',
                'if (!tomba_widescreen_enabled || !eu_ws_refresh()) return 0;')
            source=source.replace('if (!tomba_widescreen_enabled) return;',
                'if (!tomba_widescreen_enabled || !eu_ws_refresh()) { psx_mod_set_widescreen_view_anchor(0,0); return; }')
            source=source.replace('if (!enabled ||', 'if (!eu_ws_refresh() || !enabled ||')
            source=source.replace('    tomba_widescreen_scripts_tick();',
                '    if (!eu_ws_refresh()) { psx_mod_set_widescreen_view_anchor(0,0); return; }\n    tomba_widescreen_scripts_tick();')
            for callback,key in [('tomba_widescreen_anchor_camera',0x800636a4),('tomba_widescreen_tag_hud',0x8005e08c),('residency_tick',0x8005a184)]:
                signature=f'static void {callback}(CPUState* cpu, uint32_t address) {{\n    (void)address;'
                if signature in source:
                    source=source.replace(signature,signature+f'\n    if (!eu_ws_refresh() || (address&0x1fffffffu)!=(eu_ws_address(0x{key:08x}u)&0x1fffffffu)) return;')
            source += constructor
        (out/name).write_text('#include "eu_widescreen.h"\n'+source,encoding='utf-8')
    (out/'profiles.json').write_text(json.dumps([row['mapping'] for row in rows],indent=2)+'\n',encoding='utf-8')
    print('PASS: guarded EU2 widescreen bindings in five MAIN/area image sets'+
          (' (static analysis only; boot disc unqualified)' if reference_disc else ''),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-disc',type=Path,help='Static matching-image analysis only; not a boot-disc override')
    parser.add_argument('--revision',choices=('original','rev1'),help='Explicit static reference profile; production defaults to the prepared disc')
    args=parser.parse_args()
    generate(args.reference_disc,args.revision)
