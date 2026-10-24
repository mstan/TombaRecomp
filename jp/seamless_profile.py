"""Bind the shared EU planner to reviewed original SLPS-01144 instructions.

Generated C is a build artifact, not a separately maintained loader. The EU
source and its regional execution policy are explicitly pinned below.
"""
import argparse,hashlib,json,re,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'eu'),str(ROOT/'psxrecomp/tools')]
from seamless_profiles import fnv
from aot_overlay_pipeline import Disc,check_disc

MAP={0x800171b8:0x80016740,0x80017238:0x800167c0,
 0x800198b4:0x80019608,0x800199e8:0x80019728,
 0x8001a64c:0x8001a2b8,0x8001be1c:0x8001b808,0x8001be58:0x8001b844,
 0x8004eb08:0x8001f574,0x8004f010:0x8001fa48,0x8004f120:0x8001fb5c,
 0x8004f25c:0x8001fc98,0x8004f27c:0x8001fcb8,
 0x8005042c:0x80043a90,0x8005f0fc:0x8005ba48,
 0x8007460c:0x8006e148,0x80074690:0x8006e1cc,0x80074760:0x8006e29c,
 0x80078530:0x80072398,0x80099000:0x8009e000}

def generate(output=None):
 source=(ROOT/'eu/seamless/loader.c').read_text()
 assert hashlib.sha256(source.encode()).hexdigest()=='d3aa48d5dfc8bc6d791cc7862c245d971f0f95a64b5f060b70a4235e15feb019','Shared loader requires review'
 disc=Disc(ROOT/'disc/jp/disc.cue');check_disc(dict(disc_hashes={'sha256':'fb5b8ea9e3bd328e88a6b8b8ecb0b493d0dda5a9b5f732a7a6e4c9b146d9cd2b'}),disc,ROOT/'disc/jp/disc.cue')
 exe=disc.read('SLPS_011.44');assert hashlib.sha1(exe).hexdigest()=='07d577698ad31ec1a69b9d7b80a7c3f90b650888';body=exe[2048:]
 def word(pc):return struct.unpack_from('<I',body,pc-0x80010000)[0]
 def field(pc,opcode):
  hi,lo=word(pc-4),word(pc);assert hi>>26==15 and lo>>16==opcode and (hi>>16&31)==(lo>>21&31),(hex(pc),hex(hi),hex(lo))
  return ((hi&65535)<<16)+(lo&65535)-(65536 if lo&32768 else 0)
 row=dict(queue=field(0x8001f650,0x2442),files=field(0x8001f680,0x24a5),scratch=field(0x8001f764,0x2442),alternate=field(0x8001f754,0x2442),errors=field(0x8001f5b0,0xac20),headers=field(0x8001fb78,0x2484),bodies=field(0x8001fbb0,0x2484),codec_bit=field(0x8003c924,0xa020),codec_flags=field(0x8003c93c,0xa423),spu_mode=field(0x80070e28,0x8c63),spu_address=0x8009d780,game=0x8009e508,list_buffer=0,list_lba=0,list_size=0)
 assert word(0x80070e2c)==0x3c01800a and word(0x80070e30)==0xa422d780
 assert word(0x8001fbf4)==0x3c018007 and word(0x8001fbfc)==0x8c342398
 # Unlike EU, Japanese WVDs put the VAB-header table FIRST and ADPCM
 # bodies SECOND. The original loader derives s4/s2 from word 0, fp/s7
 # from word 4, then uses those bases for headers/bodies respectively.
 sound_layout_words={0x8001fae4:0x8c430000,0x8001faec:0x0043a021,
  0x8001faf0:0x8c430004,0x8001faf4:0x02809021,0x8001faf8:0x0043f021,
  0x8001fafc:0x03c0b821,0x8001fb08:0x8e430000,0x8001fb10:0x00031882,
  0x8001fb14:0x3050000f,0x8001fb90:0x02821021,0x8001fbc8:0x03c21021}
 for pc,value in sound_layout_words.items():assert word(pc)==value,hex(pc)
 # Original loader's exact leaf calls and gameTask sleep continuation.
 calls={0x80019720:0x800167c0,0x8001fa40:0x8005bd0c,0x8001fb54:0x8006e148,0x8001fc90:0x8006e29c,0x8001fcb0:0x8006e1cc}
 for pc,target in calls.items():assert word(pc)==(0x0c000000|((target&0xfffffff)>>2)),hex(pc)
 assert word(0x80019724)==0x24040001 and word(0x80019728)==0x080065ab
 for pc in [0x8001ffe4,0x800200a4,0x8002077c]:
  assert word(pc-8)==0x3c058002 and word(pc-4)==0x24a5f574
  assert word(pc)==0x0c0059d0 and word(pc+4)==0x24040002
 # BCD table: 1047 slots, including two unused zero entries. STR lengths
 # count 2336-byte sectors; movies remain on the original streaming path.
 by_lba={l:(name,n) for name,(l,n) in disc.files.items()};bcd=lambda v:(v>>4)*10+(v&15)
 files=[]
 for i in range(1047):
  at=row['files']-0x80010000+i*8;raw=body[at:at+8]
  if i in [217,218]:assert raw==bytes(8);continue
  lba=(bcd(raw[0])*60+bcd(raw[1]))*75+bcd(raw[2])-150;name,size=by_lba[lba]
  expected=size//2048*2336 if name.endswith('.STR') else size
  assert struct.unpack_from('<I',raw,4)[0]==expected,(i,name)
  files.append(dict(id=i,file=name))
 spans=[('loader_hash',0x8001f574,0x8b0),('task_hash',0x80019608,0x2cd0),('libraries_hash',0x8006e148,0x2e00),('gpu_hash',0x8005ba48,0x100),('open_hash',0x80016740,0xb4),('render_hash',0x80043a90,0x700)]
 for key,pc,size in spans:row[key]=fnv(body[pc-0x80010000:pc-0x80010000+size])
 row['files_hash']=fnv(body[row['files']-0x80010000:row['files']-0x80010000+1047*8]);row['fingerprint']=body[0x6740:0x6780]
 out=(output or ROOT/'build-jp/final/generated').resolve();assert out.is_relative_to(ROOT);out.mkdir(parents=True,exist_ok=True)
 (out/'eu_profiles.h').write_text('#define TOMBI_MAIN_IDENTITY_ADDRESS 0x80016740u\nstatic const TombiLoaderProfile eu_profiles[1] = {{'+','.join(hex(v)+'u' for k,v in row.items() if k!='fingerprint')+',{'+','.join(str(v) for v in row['fingerprint'])+'}}};\n')
 # Only reviewed regional adaptations; no EU profile or runtime edits.
 source=source.replace('n<5','n<1').replace('id >= 1119','id >= 1047').replace('p->files,1119*8','p->files,1047*8')
 source=source.replace('0x8004EB08u,0x850','0x8004EB08u,0x8b0').replace('0x800198B4u,0x3154','0x800198B4u,0x2cd0')
 # Preserve the shared planner/transfer implementation; adapt only the
 # original regional WVD layout and handle-slot semantics. No waits/restarts.
 replacements={
  'uint32_t samples=u32(p), headers=u32(p+4);':'uint32_t samples=u32(p+4), headers=u32(p);',
  'uint32_t samples=r->dest+r32(r->dest), headers=r->dest+r32(r->dest+4);':
   'uint32_t samples=r->dest+r32(r->dest+4), headers=r->dest+r32(r->dest);'}
 for old,new in replacements.items():assert source.count(old)==1;source=source.replace(old,new)
 assert source.count('if(slot==15) slot=0;')==2
 source=source.replace('if(slot==15) slot=0;','/* Japanese original retains slot 15. */')
 # Japan has resident descriptors, no language-specific GP/list DMA window.
 begin=source.index('            unsigned id=r16(r->desc);');end=source.index('            if((a<',begin)
 source=source[:begin]+'            const int load_list=0; /* No Japanese SYS/LD lists. */\n'+source[end:]
 old='return (state==0 && phase<=3) || (state==1 &&\n        (phase==0 || phase==7 || (phase>=1 && phase<=6 && phase!=3 && step==0)));'
 assert old in source
 source=source.replace(old,'return last_batch_frame==frame && state==1 &&\n        (phase==7 || (phase>=1 && phase<=6 && phase!=3 && step==0));')
 source=source.replace('static int install_batch(CPUState *cpu) {','static int install_batch(CPUState *cpu) {\n    if(diagnostic_cd_lists) { ++fallbacks; psx_mod_counter_add("tomba.jp.seamless.test_original",1); return 0; }')
 source=source.replace('TOMBI_SEAMLESS_TEST_CD_LISTS','TOMBA_JP_SEAMLESS_TEST_CD').replace('EU seamless:','JP seamless:')
 # Original script timers/intro waits and gameplay yields stay original.
 def remap(m):
  value=int(m.group(1),16)
  if value in MAP:return hex(MAP[value])+'u'
  if 0x10000<=value<0x78000 and value+0x80000000 in MAP:return hex(MAP[value+0x80000000]&0x1fffffff)+'u'
  assert not (0x80010001<=value<0x80099001),hex(value)
  return m.group()
 source=re.sub(r'0x([0-9a-fA-F]+)u\b',remap,source)
 (out/'jp_loader.c').write_text(source)
 # Reuse the shared atomic-batch/sound/VRAM safety fixture. Replace only its
 # EU-specific list-window checks and regional constants; no second planner.
 test=(ROOT/'eu/seamless/tests.c').read_text().replace('"loader.c"','"jp_loader.c"').replace('lang<5','lang<1')
 # The common synthetic guard fixture uses the EU table order; model the
 # Japanese original order here as well. Runtime banks remain unmodified.
 test=test.replace('{{0,0x100},{4,0x40}', '{{0,0x40},{4,0x100}')
 start=test.index('        /* Only the original file-0 system-list extent');end=test.index('        w32(0x1f8001d4',start)
 test=test[:start]+'''        /* Japan has no list-write exception below MAIN's end. */
        w32(s_profile->queue+126*8+4,0x8009dac8);writes=0;
        assert(!install_batch(&cpu) && !writes && !leaves);
        setup(lang);diagnostic_cd_lists=1;writes=0;
        assert(!install_batch(&cpu) && !writes && !leaves);
        diagnostic_cd_lists=0;setup(lang);frame=123;last_batch_frame=frame;
'''+test[end:]
 test=test.replace('cpu.gpr[31]=0x800199e8;cpu.gpr[4]=1;','cpu.gpr[31]=0x800199e8;cpu.gpr[4]=1;\n        assert(!loading_yield_allowed(&cpu,1,0,0,0));\n        assert(!loading_yield_allowed(&cpu,1,1,0,3)); /* scripted intro wait */\n        last_batch_frame=frame-1;assert(!loading_yield_allowed(&cpu,1,1,7,0));last_batch_frame=frame;')
 for old,new in MAP.items():test=test.replace(hex(old),hex(new))
 test=test.replace('int main(void) {','int main(int argc,char **argv) {')
 pos=test.index('    puts(')
 test=test[:pos]+'''    assert(argc==2);
    FILE *original=fopen(argv[1],"rb");assert(original);
    assert(!fseek(original,2048,SEEK_SET));
    assert(fread(memory+0x10000,1,0x8e000,original)==0x8e000);fclose(original);
    assert(validate_code());memory[0x16740]^=1;assert(!validate_code());
    puts("PASS Japan: shared atomic batches, WVD/VRAM guards, original-byte rejection, no GP exception, batch-local loading yields and original script waits");
    return 0;
}
'''
 (out/'jp_loader_tests.c').write_text(test)
 contract=dict(boot_sha1=hashlib.sha1(exe).hexdigest(),shared_loader_sha256=hashlib.sha256((ROOT/'eu/seamless/loader.c').read_text().encode()).hexdigest(),fields={k:hex(v) for k,v in row.items() if k!='fingerprint'},code_map={hex(k):hex(v) for k,v in MAP.items()},guard_spans=[dict(role=k,address=hex(pc),bytes=n,sha256=hashlib.sha256(body[pc-0x80010000:pc-0x80010000+n]).hexdigest()) for k,pc,n in spans],files=files,no_gp_list_exception=True,only_batch_local_loading_yields=True,wvd_header_table_word=0,wvd_body_table_word=1,wvd_slot_15_preserved=True)
 (out/'loader-contract.json').write_text(json.dumps(contract,indent=2)+'\n')
 print('PASS Japan loader bindings: 1047 slots, original calls/fields, no NTSC/script changes',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path);generate(p.parse_args().output)
