"""Check actual common C++ decoder metadata against original Japanese MIPS."""
import csv,hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'build-jp/full/test-deps'),str(ROOT/'tools'),str(ROOT/'psxrecomp/tools')]
from seamless_asset_probe import DecoderOracle,decode_gam
from aot_overlay_pipeline import Disc

def main():
 disc=Disc(ROOT/'disc/jp/disc.cue');exe=disc.read('SLPS_011.44');assert hashlib.sha1(exe).hexdigest()=='07d577698ad31ec1a69b9d7b80a7c3f90b650888'
 oracle=DecoderOracle(exe,entry=0x8003c8c4);seen={};count=0
 for row in csv.DictReader((ROOT/'build-jp/rc2-analysis/codec-states.csv').open()):
  raw=disc.read(row['file']);key=hashlib.sha256(raw).hexdigest()
  if key not in seen:
   decoded=decode_gam(raw);oracle.verify(raw,decoded)
   bit=bytes(oracle.uc.mem_read(0x9dbd0,1))[0];flags=struct.unpack('<H',bytes(oracle.uc.mem_read(0x9dbd4,2)))[0]
   seen[key]=(flags|(bit<<16),len(decoded))
  state,n=seen[key]
  assert int(row['state'])==state and int(row['decoded_len'])==n,(row,state,n)
  count+=1
 assert count==638 and len(seen)==403
 report=dict(result='passed',actual_cpp_resident_decoder=True,original_mips_files=count,unique_streams=len(seen),two_destination_fills=True,final_codec_bit_and_flags_match=True,scope='Decoder output and state only; regular gameplay is separately tested')
 (ROOT/'build-jp/rc2-analysis/codec-state-result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
if __name__=='__main__':main()
