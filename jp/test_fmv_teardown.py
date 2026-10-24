"""Synthetic leaf fixtures: original Japanese MIPS movie-end comparison.

These are not gameplay or endgame acceptance. Real New Game is tested separately.
"""
import hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'build-jp/full/test-deps'))
from unicorn import Uc,UC_ARCH_MIPS,UC_MODE_MIPS32,UC_MODE_LITTLE_ENDIAN,UC_HOOK_CODE
from unicorn import mips_const as R

def main():
 exe=(ROOT/'disc/jp/SLPS_011.44').read_bytes();assert hashlib.sha1(exe).hexdigest()=='07d577698ad31ec1a69b9d7b80a7c3f90b650888'
 uc=Uc(UC_ARCH_MIPS,UC_MODE_MIPS32|UC_MODE_LITTLE_ENDIAN);uc.mem_map(0,0x200000);uc.mem_map(0x1f800000,4096)
 def write(a,b):uc.mem_write(a&0x1fffffff,b)
 def u32(a,v):write(a,struct.pack('<I',v))
 calls=[]
 def stub(uc,pc,size,user):
  if pc==0x80063ee0:
   u32(uc.reg_read(R.UC_MIPS_REG_A0),0x80110000);u32(uc.reg_read(R.UC_MIPS_REG_A1),0x80120000)
  elif pc==0x80061bd4:calls.append('CdMix')
  elif pc not in [0x8005a670,0x80063dec]:return
  uc.reg_write(R.UC_MIPS_REG_V0,0);uc.reg_write(R.UC_MIPS_REG_PC,uc.reg_read(R.UC_MIPS_REG_RA))
 uc.hook_add(UC_HOOK_CODE,stub)
 original=exe[2048:];totals=original[0x61d3c:0x61d3c+44];rows=[]
 for mid in range(22):
  for enabled in [False,True]:
   write(0x80010000,original);write(0x801fd870,bytes(0x70));write(0x80100000,bytes(64))
   u32(0x1f8001d4,0x801fd870);write(0x1f8001cd,bytes([mid]));write(0x801fd8d8,b'\x01')
   write(0x801fd8b8,struct.pack('<H',2));write(0x80120000,bytes(32));u32(0x80120008,2)
   write(0x80120010,struct.pack('<HH',320,240))
   if enabled:write(0x80071d3c+mid*2,struct.pack('<H',3))
   calls.clear();uc.reg_write(R.UC_MIPS_REG_A0,0x80100000);uc.reg_write(R.UC_MIPS_REG_SP,0x801ef000);uc.reg_write(R.UC_MIPS_REG_RA,0x80000000)
   uc.emu_start(0x8001d414,0x80000000,count=100000)
   assert uc.reg_read(R.UC_MIPS_REG_PC)==0x80000000
   state=struct.unpack('<H',bytes(uc.mem_read(0x1fd8b8,2)))[0]
   assert state==(3 if enabled else 2) and calls==(['CdMix'] if enabled else []),(mid,enabled,state,calls)
   actual=bytearray(uc.mem_read(0x71d3c,44));expected=bytearray(totals)
   if enabled:expected[mid*2:mid*2+2]=struct.pack('<H',3)
   assert actual==expected
  rows.append(dict(movie_id=mid,original_state_preserved_when_off=True,original_end_state_and_mix_when_on=True,only_active_total_changed=True))
 out=ROOT/'build-jp/rc2-analysis/fmv-teardown.json';out.write_text(json.dumps(dict(result='passed',scope='Synthetic original-MIPS leaf fixtures, not live endgame acceptance',movies=rows,ram_used_only_in_isolated_oracle=True),indent=2)+'\n')
 print('PASS: 22 Japanese original-MIPS movie teardown ON/OFF fixtures; only active total changed')
if __name__=='__main__':main()
