"""Read-only Japan follow-up; candidates are never enabled by this script."""
import hashlib,importlib.util,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'eu2'),str(ROOT/'psxrecomp/tools')]
from widescreen_analysis import mask
from aot_overlay_pipeline import Disc,check_disc
def main():
    d=Disc(ROOT/'disc/jp/disc.cue');e=Disc(ROOT/'disc/Tombi! (Europe) (En,Fr,De,It,Nl) (Rev 1).cue')
    check_disc(dict(disc_hashes={'sha256':'fb5b8ea9e3bd328e88a6b8b8ecb0b493d0dda5a9b5f732a7a6e4c9b146d9cd2b'}),d,ROOT/'disc/jp/disc.cue')
    body=d.read('SLPS_011.44')[2048:]
    def word(pc):return struct.unpack_from('<I',body,pc-0x80010000)[0]
    def jal(pc):
        w=word(pc);assert w>>26==3;return 0x80000000|((w&0x3ffffff)<<2)
    report={'implemented':False,'source':'original Japan disc, original callers, existing psx_tomba symbol aliases',
      'event_predicate':{'eu1':'0x80020a78','jp':hex(jal(0x800576cc)),'original_caller':'0x800576cc','return_continuation':'0x800576d4','different_body':True},
      'hud_parent':{'eu1':'0x80058680','jp':'0x8004ba68','stack_frame_bytes':0x90,
        'callee_returns':[{'eu1':hex(a),'jp':hex(b),'jp_callee':hex(jal(b-8))} for a,b in [(0x800586dc,0x8004bac4),(0x800586ec,0x8004bad4),(0x80058700,0x8004bae4),(0x80058710,0x8004baf4)]]},
      'overlay_link':{'jp':'0x800e9af8','original_materialization':['0x8002025c','0x80020260']},'overlays':[]}
    assert word(0x8002025c)==0x3c06800f and word(0x80020260)==0x24c69af8
    assert word(0x8004ba68)==0x27bdff70
    for area,sites in [(0,[0x801175cc,0x801176c4]),(1,[0x80116b04,0x80116bec])]:
        src=e.read(f'SYSTEM/X0{area:02d}.BIN');dst=d.read(f'SYSTEM/X{area:02d}.BIN');dw=[mask(w) for w in struct.unpack('<%dI'%(len(dst)//4),dst[:len(dst)//4*4])]
        for site in sites:
            at=site-0x800e8050;pat=[mask(w) for w in struct.unpack('<16I',src[at-32:at+32])]
            matches=[i for i in range(len(dw)-16) if dw[i:i+16]==pat]
            row={'area':area,'eu1':hex(site),'candidates':[hex(0x800e9af8+(i+8)*4) for i in matches]}
            if len(matches)==1:
                off=(matches[0]+8)*4;row.update(word=hex(struct.unpack_from('<I',dst,off)[0]),window_sha256=hashlib.sha256(dst[off-32:off+32]).hexdigest())
            report['overlays'].append(row)
    report['remaining_tests']=['Prove Japanese HUD stack/parent ownership for each primitive class, including Japanese message glyphs.',
       'Review all changed raw immediates and pool/camera structure offsets; normalized pattern matches are candidates only.',
       'Review area-0 anchor call target and area-1 roof boundary constants against original Japan scripts.',
       'Regenerate Japanese MAIN and native overlays with NTSC widescreen signatures and audit the new config namespace.',
       'Real controller-only 4:3/wide paired gameplay captures, HUD/world sprite tags, finite-background 4:3 scene, roofs and return route.']
    out=ROOT/'build-widescreen/japan-bindings.json';out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
