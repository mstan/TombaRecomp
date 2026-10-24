"""Compare the shared GAM decoder with original Japanese MIPS instructions.

This proves codec equivalence only, not a seamless-loading integration.
"""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'psxrecomp/tools')]
from seamless_asset_probe import DecoderOracle,decode_gam
from aot_overlay_pipeline import Disc

def main():
 disc=Disc(ROOT/'disc/jp/disc.cue');exe=disc.read('SLPS_011.44')
 assert hashlib.sha1(exe).hexdigest()=='07d577698ad31ec1a69b9d7b80a7c3f90b650888'
 oracle=DecoderOracle(exe,entry=0x8003C8C4);cases=[]
 for name in sorted(disc.files):
  if not name.endswith('.GAM'):continue
  encoded=disc.read(name)
  if encoded[:4]!=b'GAM\0':continue
  decoded=decode_gam(encoded);oracle.verify(encoded,decoded)
  cases.append(dict(file=name,decoded_sha256=hashlib.sha256(decoded).hexdigest()))
 assert len(cases)==638,len(cases)
 report=dict(result='passed',original_mips_entry='0x8003C8C4',destination_fill_patterns=2,files=len(cases),seamless_loading_proven=False,cases=cases)
 out=ROOT/'build-jp/full/codec-differential.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2)+'\n')
 print('PASS original Japanese MIPS/shared decoder:',len(cases),'files',flush=True)
if __name__=='__main__':main()
