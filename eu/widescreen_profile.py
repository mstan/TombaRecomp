"""Bind the shared widescreen implementation to verified PAL MAIN/area images.

Only project source and address/hash metadata are generated. Original disc bytes
stay in ignored build outputs. The US implementation remains the single owner
of HUD, camera, residency and script policy.
"""
import hashlib
import json
from pathlib import Path
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
# Return sites and entry points mapped by matching complete instruction windows,
# then independently checked across all five original MAIN images.
CODE = {
    0x80022c34:0x800200a4, 0x80022d68:0x800201d8,
    0x80022e44:0x800202b4, 0x80022e78:0x800202e8,
    0x80022e80:0x800202f0, 0x80022f94:0x80020404,
    0x80022f9c:0x8002040c, 0x80022fe8:0x80020458,
    0x80022ff0:0x80020460, 0x80023068:0x800204d8,
    0x80023070:0x800204e0, 0x800230fc:0x8002056c,
    0x80023608:0x80020a78, 0x8002a1e4:0x800276c0,
    0x8003d8b8:0x8003a464, 0x8003e828:0x8003b3d4,
    0x8004a170:0x80054338, 0x8004e4c4:0x800586dc,
    0x8004e4d4:0x800586ec, 0x8004e4e8:0x80058700,
    0x8004e4f8:0x80058710, 0x8004e62c:0x80058844,
    0x8004e6b8:0x800588d0, 0x8004e6dc:0x800588f4,
    0x8004e7ac:0x800589c4, 0x8004e830:0x80058a48,
    0x8004e9ac:0x80058bc4, 0x8004ead0:0x80058ce8,
    0x8004edec:0x80059004, 0x8004ee18:0x80059030,
    0x8004ee44:0x8005905c, 0x8004ee70:0x80059088,
    0x8004ee9c:0x800590b4, 0x8004eef4:0x8005910c,
    0x8004f330:0x80059548, 0x8004f450:0x80059668,
    0x8005a184:0x8004c1ec, 0x8005a564:0x8004c5cc,
    0x8005a5f8:0x8004c660, 0x8005aa98:0x8004cb00,
    0x8005e08c:0x8005e634, 0x800636a4:0x80063c4c,
}
# Exact LUI + low-immediate pairs in the original EU code, not a regional delta.
FIELDS = {0x8009bcc8:0x80017848, 0x800a38b8:0x80017e1c,
          0x800a3d08:0x80017ef0, 0x800a5970:0x80017694,
          0x800b0b88:0x80018030, 0x8007b296:0x8004c2dc}
TABLES = {0x8007eefc:0x8007b73c, 0x8007f0cc:0x8007b90c}
OVERLAY = {0x801168f4:0x801175cc,0x801169ec:0x801176c4,
           0x80115e2c:0x80116b04,0x80115f14:0x80116bec}
# A policy edit must review its PAL substitutions too. Normalize line endings
# so an ordinary Windows checkout does not change this source contract.
SOURCES = {
    'tomba_widescreen_scene.h':'c0adc0a86a6dd2c71c7141121510e9ac8a760bf328e11e5240f63d96e554daf7',
    'tomba_widescreen_plugin.c':'2e5406a062d5f36046dee6ed0688b43ed55ce413c5fce3cbe580c5afb716eb0c',
    'tomba_widescreen_residency.c':'325c9649ddd0941bd3ad0d50c8fe1127afbe41580157e37520ca887b0129b80e',
    'tomba_widescreen_scripts.c':'d1e8df51e0cc65d98122f931a6b74ec44df01e3a95fc875fc3b08c9a3b78e056',
    'tomba_widescreen_hud.h':'668942a6788b975896fd563965d5bd6ed8a0d0ea3f74901caf48d43a1c8fe0fe',
    'tomba_widescreen_sprites.h':'caced2ac90e596beaa2cb852125f2ca41b6cffa0915e42ad23da28bbea242585',
}

def generate():
    sys.path[:0] = [str(ROOT/'eu'),str(ROOT/'psxrecomp/tools')]
    from aot_overlay_pipeline import Disc
    from disc_identity import main_fingerprints
    from session_state import profiles
    disc = Disc(ROOT/'disc/Tombi! (Europe) (En,Fr,De,It,Nl) (Rev 1).cue')
    offset, identities = main_fingerprints(ROOT)
    _, games = profiles(ROOT)
    rows=[]; contracts=[]
    for i,lang in enumerate(('en','fr','de','it','nl')):
        body=(ROOT/f'disc/EXE/MAIN{i}.EXE').read_bytes()[2048:]
        def word(pc):return struct.unpack_from('<I',body,pc-0x80010000)[0]
        row={}
        for old,pc in FIELDS.items():
            low=word(pc); high=word(pc-4)
            assert high>>26==15 and high>>16&31==low>>21&31
            assert low>>26 in (9,37)
            row[old]=((high&65535)<<16)+(low&65535)-(65536 if low&32768 else 0)
        assert row[0x8009bcc8]==games[lang]['base']
        row[0x8009bcca]=row[0x8009bcc8]+2
        for old,pc in TABLES.items():
            # Both tables are shared by the five MAIN variants.
            row[old]=pc
        assert word(row[0x8007f0cc])==row[0x8007eefc]
        assert word(row[0x8007eefc])==0x1f800358
        assert word(0x8003a45c)==0x0c0080ad and word(0x8003b3cc)==0x0c0080ad
        assert word(0x8004c5c4)==0x0c0132c0 # real constructor return continuation
        assert word(0x800202e8)==0x24420040 and word(0x800202f0)==0x2c4201c1
        assert word(0x80020318)==0x2c420171 # unchanged script visibility height
        assert word(0x8005e634)==0x10a00004 # SetShadeTex
        # Capture exact instruction words around each entry/return site. Hashes
        # are checked against the committed contract before any build succeeds.
        checks={hex(pc):hashlib.sha256(body[pc-0x80010000-16:pc-0x80010000+16]).hexdigest()
                for pc in sorted(set(CODE.values()))}
        for area in (0,1):
            raw=disc.read(f'SYSTEM/X{i}{area:02}.BIN')
            assert word(0x8004f624)==0x3c06800f
            low=word(0x8004f628)
            assert low&0xffff0000==0x24c60000
            base=0x800f0000+(low&65535)-(65536 if low&32768 else 0)
            for old,pc in OVERLAY.items():
                if (old in (0x801168f4,0x801169ec)) != (area==0):continue
                pc=base+(pc-0x800e8050);row[old]=pc
                at=pc-base; w=struct.unpack_from('<I',raw,at)[0]
                assert w=={0x801168f4:0x27bdffe8,0x801169ec:0x0c00a8f5,
                           0x80115e2c:0x28420b6e,0x80115f14:0x28620b6d}[old]
                checks[hex(pc)]=hashlib.sha256(raw[at-16:at+16]).hexdigest()
        rows.append(row);contracts.append(dict(language=lang,checks=checks))
    contract=ROOT/'eu/widescreen-contract.json'
    if not contract.exists():
        raise RuntimeError('Missing reviewed EU widescreen instruction contract')
    assert json.loads(contract.read_text())==contracts,'EU widescreen instruction contract mismatch'
    out=ROOT/'build-eu-seamless/generated/widescreen';out.mkdir(parents=True,exist_ok=True)
    header='''/* Generated PAL adapter; project source only. */
#pragma once
#include <stdint.h>
int eu_ws_refresh(void);
uint32_t eu_ws_address(uint32_t);
'''
    (out/'eu_widescreen.h').write_text(header)
    impl=['#include "mod_plugins.h"','#include "eu_widescreen.h"',
          'static int language = -1;',
          'static const uint32_t identity[5][16] = {']
    for lang in ('en','fr','de','it','nl'):
        impl.append('{'+','.join(hex(w)+'u' for w in struct.unpack('<16I',identities[lang]))+'},')
    impl+=['};','int eu_ws_refresh(void) {','language=-1;',
           'if (!psx_mod_game_started()) return 0;',
           'for (unsigned i=0;i<5;i++) { unsigned n;',
           f'for(n=0;n<16;n++) if(psx_mod_read_word(0x{0x80010000+offset:08x}u+n*4)!=identity[i][n]) break;',
           'if(n==16) { language=(int)i; return 1; } } return 0; }',
           'uint32_t eu_ws_address(uint32_t address) {',
           'if(language<0) return 0;', 'switch(address) {']
    for old in rows[0]:
        impl.append('case '+hex(old)+'u: { static const uint32_t a[5] = {'+
                    ','.join(hex(r[old])+'u' for r in rows)+'}; return a[language]; }')
    impl+=['default:return address;','}}']
    (out/'eu_widescreen.c').write_text('\n'.join(impl)+'\n')
    for name in SOURCES:
        source=(ROOT/'src/mods'/name).read_text()
        assert hashlib.sha256(source.encode()).hexdigest()==SOURCES[name], \
            f'Review PAL widescreen bindings after shared policy changes: {name}'
        # Static pool descriptors keep their US keys; map at each use so their
        # bases follow the selected MAIN and never persist across a restore.
        pool=re.search(r'static const Pool pools\[\] = \{.*?\n\};',source,re.S)
        descriptor=pool.group(0) if pool else None
        if descriptor:source=source.replace(descriptor,'/* POOL_DESCRIPTORS */')
        def replace(m):
            old=int(m.group(1),16)
            if old in CODE:return hex(CODE[old])+'u'
            if old in rows[0]:return f'eu_ws_address(0x{old:08x}u)'
            if old in (0x8000fe00,0x80098000,0x801fffb8,0x801ffffc,0x80200000):return m.group(0)
            raise ValueError(f'Unmapped guest address {m.group(0)} in {name}')
        # Include comments in the conversion audit, but only replace C literals.
        source=re.sub(r'0x(80[0-9a-fA-F]{6})u\b',replace,source)
        source=source.replace('0x0C00B3BEu','0x0C00A8F5u').replace('0x0C008B91u','0x0C0080ADu')
        source=source.replace('0x22E44u','0x202B4u')
        if descriptor:
            source=source.replace('/* POOL_DESCRIPTORS */',descriptor)
            source=source.replace('pools[p].base','eu_ws_address(pools[p].base)')
        # Guard every callback that can observe/write guest state. Profile is
        # reconstructed from live MAIN bytes, including after language/restore.
        source=source.replace('if (!tomba_widescreen_enabled) return 0;',
            'if (!tomba_widescreen_enabled || !eu_ws_refresh()) return 0;')
        source=source.replace('if (!tomba_widescreen_enabled) return;',
            'if (!tomba_widescreen_enabled || !eu_ws_refresh()) { psx_mod_set_widescreen_view_anchor(0,0); return; }')
        source=source.replace('if (!enabled ||', 'if (!eu_ws_refresh() || !enabled ||')
        source=source.replace('    tomba_widescreen_scripts_tick();',
            '    if (!eu_ws_refresh()) { psx_mod_set_widescreen_view_anchor(0,0); return; }\n    tomba_widescreen_scripts_tick();')
        (out/name).write_text('#include "eu_widescreen.h"\n'+source)
    (out/'profiles.json').write_text(json.dumps([{hex(k):hex(v) for k,v in r.items()} for r in rows],indent=2)+'\n')
    print('PASS: checked widescreen HUD/camera/cull/residency/script bindings in five original MAIN images',flush=True)

if __name__=='__main__':generate()
