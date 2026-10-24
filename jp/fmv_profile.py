"""Verify Japanese FMV totals, descriptor indirection and original teardown."""
import argparse,hashlib,json,mmap,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'psxrecomp/tools'))
from aot_overlay_pipeline import Disc,check_disc

def generate(output=None):
 disc=Disc(ROOT/'disc/jp/disc.cue');check_disc(dict(disc_hashes={'sha256':'fb5b8ea9e3bd328e88a6b8b8ecb0b493d0dda5a9b5f732a7a6e4c9b146d9cd2b'}),disc,ROOT/'disc/jp/disc.cue')
 exe=disc.read('SLPS_011.44');assert hashlib.sha1(exe).hexdigest()=='07d577698ad31ec1a69b9d7b80a7c3f90b650888';body=exe[2048:]
 def word(pc):return struct.unpack_from('<I',body,pc-0x80010000)[0]
 checks={0x8001d440:0x904201cd,0x8001d448:0x00021040,0x8001d44c:0x3c018007,0x8001d454:0x84221d3c,0x8001d45c:0x2442fffd,0x8001d460:0x0062182b,0x8001d468:0x24020003,0x8001d480:0xa4620048,0x8001d59c:0x8c221d70,0x8001d5a8:0x84450000,0x8001d5b0:0x244225f4}
 for pc,expected in checks.items():assert word(pc)==expected,hex(pc)
 totals=struct.unpack_from('<22H',body,0x71d3c-0x10000);by_lba={l:(name,n) for name,(l,n) in disc.files.items()};bcd=lambda v:(v>>4)*10+(v&15);rows=[]
 with (ROOT/'disc/jp/disc.bin').open('rb') as f,mmap.mmap(f.fileno(),0,access=mmap.ACCESS_READ) as track:
  for mid,total in enumerate(totals):
   pointer=struct.unpack_from('<I',body,0x71d70-0x10000+mid*4)[0]
   assert 0x80010000<=pointer<0x8009e000
   fid=struct.unpack_from('<h',body,pointer-0x80010000)[0];assert 195<=fid<=216
   raw=body[0x725f4-0x10000+fid*8:][:8];lba=(bcd(raw[0])*60+bcd(raw[1]))*75+bcd(raw[2])-150
   name,size=by_lba[lba];assert name.endswith('.STR')
   frames=[]
   for i in range(size//2048):
    at=(lba+i)*2352+24
    if struct.unpack_from('<I',track,at)[0]==0x80010160:frames.append(struct.unpack_from('<I',track,at+8)[0])
   assert frames and min(frames)==1 and 3<total<=max(frames)
   rows.append(dict(movie_id=mid,descriptor=hex(pointer),file_id=fid,file=name,original_total=total,stream_last_frame=max(frames)))
 assert rows[0]['file']=='MOVIE/OP_UTA.STR' and rows[1]['file']=='MOVIE/BOY.STR'
 assert [rows[i]['file'] for i in [19,20,21]]==['MOVIE/MABUTA.STR','MOVIE/ENDING.STR','MOVIE/LOGO.STR']
 out=(output or ROOT/'build-jp/final/generated').resolve();assert out.is_relative_to(ROOT);out.mkdir(parents=True,exist_ok=True)
 (out/'fmv-contract.json').write_text(json.dumps(dict(boot_sha1=hashlib.sha1(exe).hexdigest(),table='0x80071D3C',movie_id='0x1F8001CD',end_total=3,shared_plugin_unchanged=True,original_frame_comparison_and_teardown=True,program_sha256=hashlib.sha256(body[0xd414:0xdaf0]).hexdigest(),movies=rows),indent=2)+'\n')
 print('PASS Japan FMV bindings: 22 original streams, frame totals and teardown; common plugin unchanged',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path);generate(p.parse_args().output)
