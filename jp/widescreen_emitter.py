"""Existing checked regional adapter emitter; shared renderer policy stays in src/mods."""
import hashlib,re,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=0x80010000
sys.path.insert(0,str(ROOT/"eu"))
import widescreen_profile as shared

def emit(rows,codes,offset,identities,out,overlay_call='0x0C00A8E2u',script_call='0x0C0080ADu'):
    out.mkdir(parents=True,exist_ok=True)
    (out/'eu_widescreen.h').write_text('#pragma once\n#include "mod_plugins.h"\nint eu_ws_refresh(void);\nuint32_t eu_ws_address(uint32_t);\nuint32_t eu_ws_code_key(uint32_t);\nint eu_ws_register_entry_plugin(const char*,uint32_t,PSXModFunctionEntryCallback);\n')
    impl=['#include "mod_plugins.h"','#include "cpu_state.h"','#include "eu_widescreen.h"','static int language=-1;',f'static const uint32_t identity[{len(rows)}][16]={{']
    for lang in identities:impl.append('{'+','.join(hex(v)+'u' for v in struct.unpack('<16I',identities[lang]))+'},')
    impl+=['};','int eu_ws_refresh(void){language=-1;if(!psx_mod_game_started())return 0;',f'for(unsigned i=0;i<{len(rows)};i++){{unsigned n;for(n=0;n<16;n++)if(psx_mod_read_word({hex(BASE+offset)}u+n*4)!=identity[i][n])break;if(n==16){{language=(int)i;return 1;}}}}return 0;}}',
      'uint32_t eu_ws_address(uint32_t a){if(language<0)return 0;switch(a){']
    for old in rows[0]:impl.append('case '+hex(old)+f'u:{{static const uint32_t a[{len(rows)}]={{'+','.join(hex(row[old])+'u' for row in rows)+'};return a[language];}')
    impl+=['default:return a;}}','uint32_t eu_ws_code_key(uint32_t a){if(language<0)return 0;']
    for key in codes:impl.append('if(a==eu_ws_address('+hex(key)+'u))return '+hex(key)+'u;')
    impl+=['return 0;}',
      'static struct {uint32_t key;PSXModFunctionEntryCallback callback;} hooks[8];static unsigned hook_count;',
      'static void entry(CPUState* cpu,uint32_t address){if(!eu_ws_refresh())return;for(unsigned i=0;i<hook_count;i++)if(address==eu_ws_address(hooks[i].key))hooks[i].callback(cpu,address);}',
      'int eu_ws_register_entry_plugin(const char* name,uint32_t key,PSXModFunctionEntryCallback callback){if(hook_count>=8)return 0;hooks[hook_count].key=key;hooks[hook_count++].callback=callback;switch(key){']
    for key in (0x800636a4,0x8005e08c,0x8005a184):
        impl.append('case '+hex(key)+'u:')
        for value in sorted({r[key] for r in rows}):impl.append('(void)psx_mod_register_function_entry_plugin(name,'+hex(value)+'u,entry);')
        impl.append('return 1;')
    impl+=['default:return 0;}}'];(out/'eu_widescreen.c').write_text('\n'.join(impl)+'\n')
    for name,sha in shared.SOURCES.items():
        source=(ROOT/'src/mods'/name).read_text();assert hashlib.sha256(source.encode()).hexdigest()==sha
        pool=re.search(r'static const Pool pools\[\] = \{.*?\n\};',source,re.S);descriptor=pool.group(0) if pool else None
        if descriptor:source=source.replace(descriptor,'/* POOL_DESCRIPTORS */')
        registrations={}
        cases={}
        def case(match):
            key='WS_CASE_'+match.group(1)[2:-1];cases[key]=match.group(1);return 'case '+key+':'
        source=re.sub(r'case (0x[0-9a-fA-F]+u):',case,source)
        if cases:source=source.replace('switch (ra)', 'switch (eu_ws_code_key(ra))')
        def registration(match):
            key='WS_ENTRY_'+match.group(2)[2:-1]
            registrations[key]=match.group(2)
            return 'eu_ws_register_entry_plugin('+match.group(1)+key+match.group(3)
        source=re.sub(r'psx_mod_register_function_entry_plugin\((\s*"[^"]+",\s*)(0x[0-9a-fA-F]+u)(,\s*\w+\))',registration,source)
        def replace(match):
            old=int(match.group(1),16)
            if old in rows[0]:return f'eu_ws_address(0x{old:08x}u)'
            if old in (0x8000fe00,0x80098000,0x801fffb8,0x801ffffc,0x80200000):return match.group(0)
            raise ValueError('Unmapped literal '+match.group(0))
        source=re.sub(r'0x(80[0-9a-fA-F]{6})u\b',replace,source)
        for key,value in registrations.items():source=source.replace(key,value)
        for key,value in cases.items():source=source.replace(key,value)
        source=source.replace('0x0C00B3BEu',overlay_call).replace('0x0C008B91u',script_call).replace('0x22E44u',hex(codes[0x80022e44]&0x1fffffff)+'u')
        if descriptor:source=source.replace('/* POOL_DESCRIPTORS */',descriptor).replace('pools[p].base','eu_ws_address(pools[p].base)')
        source=source.replace('if (!tomba_widescreen_enabled) return 0;',
            'if (!tomba_widescreen_enabled || !eu_ws_refresh()) return 0;')
        source=source.replace('if (!tomba_widescreen_enabled) return;','if (!tomba_widescreen_enabled || !eu_ws_refresh()) { psx_mod_set_widescreen_view_anchor(0,0); return; }')
        source=source.replace('if (!enabled ||','if (!eu_ws_refresh() || !enabled ||')
        source=source.replace('    tomba_widescreen_scripts_tick();','    if (!eu_ws_refresh()) { psx_mod_set_widescreen_view_anchor(0,0); return; }\n    tomba_widescreen_scripts_tick();')
        (out/name).write_text('#include "eu_widescreen.h"\n'+source)

