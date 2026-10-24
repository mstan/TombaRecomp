"""Experimental Japan bindings; emit the same shared policy as EU2."""
import argparse,hashlib,importlib.util,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'eu'),str(ROOT/'eu2'),str(ROOT/'psxrecomp/tools')]
from aot_overlay_pipeline import Disc,check_disc
spec=importlib.util.spec_from_file_location('eu2_ws_emitter',ROOT/'jp/widescreen_emitter.py')
emitter=importlib.util.module_from_spec(spec);spec.loader.exec_module(emitter)
shared=emitter.shared
def generate(capture=False):
    contract=ROOT/'jp/widescreen-contract.json'
    disc=Disc(ROOT/'disc/jp/disc.cue')
    check_disc(dict(disc_hashes={'sha256':'fb5b8ea9e3bd328e88a6b8b8ecb0b493d0dda5a9b5f732a7a6e4c9b146d9cd2b'}),disc,ROOT/'disc/jp/disc.cue')
    raw=disc.read('SLPS_011.44');assert hashlib.sha1(raw).hexdigest()=='07d577698ad31ec1a69b9d7b80a7c3f90b650888'
    body=raw[2048:]
    def word(pc):return struct.unpack_from('<I',body,pc-0x80010000)[0]
    if capture:
        assert not contract.exists()
        candidates=json.loads((ROOT/'build-widescreen/discovery.json').read_text())['jp']['rows']
        mapping={int(r['eu1'],16):int(r.get('address',r.get('aligned_candidate','0')),16) for r in candidates}
        mapping.update({0x80017e1c:0x800173f0,0x80020a78:0x800219f0,0x8004f624:0x8002025c,0x8004f628:0x80020260,
          0x800586dc:0x8004bac4,0x800586ec:0x8004bad4,0x80058700:0x8004bae4,0x80058710:0x8004baf4})
        assert all(mapping.values())
    else:mapping={int(k,16):int(v,16) for k,v in json.loads(contract.read_text())['mapping'].items()}
    code={old:mapping[eu1] for old,eu1 in shared.CODE.items()};row={}
    for old,eu1 in shared.FIELDS.items():
        pc=mapping[eu1];lo=word(pc);hi=word(pc-4)
        assert hi>>26==15 and hi>>16&31==lo>>21&31 and lo>>26 in (9,37)
        row[old]=((hi&65535)<<16)+(lo&65535)-(65536 if lo&32768 else 0)
    row[0x8009bcca]=row[0x8009bcc8]+2
    row.update({old:mapping[pc] for old,pc in shared.TABLES.items()})
    assert row[0x8009bcc8]==0x8009e508
    assert word(row[0x8007f0cc])==row[0x8007eefc] and word(row[0x8007eefc])==0x1f800358
    assert word(code[0x8005e08c])==0x10a00004
    assert word(code[0x8003d8b8]-8)==0x0c00848b and word(code[0x8003e828]-8)==0x0c00848b
    assert word(0x800576cc)==0x0c00867c and code[0x80023608]==0x800219f0
    assert word(0x8004ba68)==0x27bdff70
    for site,target in [(0x8004bac4,0x8004bb8c),(0x8004bad4,0x8004bd10),(0x8004bae4,0x8004befc),(0x8004baf4,0x8004c2f0)]:
        assert word(site-8)==0x0c000000|((target&0xfffffff)>>2)
    assert word(0x8002025c)==0x3c06800f and word(0x80020260)==0x24c69af8
    overlays={0x801168f4:(0,0x8011679c,0x27bdffe8),0x801169ec:(0,0x80116894,0x0c00ac78),
              0x80115e2c:(1,0x80115db0,0x28420b6e),0x80115f14:(1,0x80115e98,0x28620b6d)}
    checks={hex(pc):hashlib.sha256(body[pc-0x80010000-32:pc-0x80010000+32]).hexdigest() for pc in sorted(set(mapping.values()))}
    for old,(area,pc,expected) in overlays.items():
        image=disc.read(f'SYSTEM/X{area:02d}.BIN');at=pc-0x800e9af8
        assert struct.unpack_from('<I',image,at)[0]==expected
        row[old]=pc;checks[hex(pc)]=hashlib.sha256(image[at-32:at+32]).hexdigest()
    row.update(code)
    evidence=dict(main_sha256=hashlib.sha256(raw).hexdigest(),mapping={hex(k):hex(v) for k,v in mapping.items()},checks=checks,data={hex(k):hex(v) for k,v in row.items()})
    if capture:contract.write_text(json.dumps(evidence,indent=2)+'\n')
    assert json.loads(contract.read_text())==evidence,'Japan reviewed contract mismatch'
    # Fixed original boot-function fingerprint, checked again for every callback.
    offset=0x6740;identity={'jp':body[offset:offset+64]}
    emitter.emit([row],code,offset,identity,ROOT/'build-jp/widescreen/generated/adapter',overlay_call='0x0C00AC78u',script_call='0x0C00848Bu')
    print('PASS Japan original MAIN, HUD callgraph, area-0/1 hook contracts; shared renderer policy',flush=True)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--capture-contract',action='store_true');generate(p.parse_args().capture_contract)
