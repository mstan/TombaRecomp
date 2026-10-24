"""Original EU2 selector metadata; never write to the original executable."""
from pathlib import Path
import hashlib,struct
ROOT=Path(__file__).resolve().parents[1]
def generate():
 data=(ROOT/'disc/eu2/SCES_013.31').read_bytes()
 assert hashlib.sha256(data).hexdigest()=='dc65210e6601cbb4ab1cc0878a73f926a2ffd1bd3d8d7923d781164fd2835f29'
 def word(pc):return struct.unpack_from('<I',data,2048+pc-0x80010000)[0]
 expected={0x80010e50:0x27bdff88,0x80010f98:0x240203e8,0x80010fb0:0xac22f0a4,0x800111c0:0x30624000,0x800111c4:0x10400038,0x800112c4:0x8c63f0a4,0x800112cc:0x2463ffff,0x800112d4:0xac23f0a4,0x800112d8:0x14620039}
 for pc,v in expected.items():assert word(pc)==v,hex(pc)
 value=2166136261
 for b in data[2048+0xe50:2048+0x14a4]:value=((value^b)*16777619)&0xffffffff
 out=ROOT/'build-eu2-seamless/generated/eu_boot_profile.inc';out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(f'#define TOMBI_SELECTOR_HASH 0x{value:08X}u\n#define TOMBI_SELECTOR_START 0x80010E50u\n#define TOMBI_SELECTOR_END 0x800114A4u\n#define TOMBI_SELECTOR_BRANCH 0x800112D8u\n#define TOMBI_SELECTOR_TIMER 0x800AF0A4u\n')
 print('PASS original EU2 selector/explicit Cross path verified')
if __name__=='__main__':generate()
