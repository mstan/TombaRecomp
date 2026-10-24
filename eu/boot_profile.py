"""Verify the original Rev-1 selector and emit only its guard metadata."""
from pathlib import Path
import hashlib
import struct

ROOT=Path(__file__).resolve().parents[1]


def generate():
    data=(ROOT/'disc/SCES_013.30').read_bytes()
    assert hashlib.sha256(data).hexdigest()=='08436f44ca2ddf9f9a9ece58f7fbbb9b88f6ab3cef6ede5b36300f51e4356df0'
    base=struct.unpack_from('<I',data,0x18)[0]
    def word(pc):return struct.unpack_from('<I',data,2048+pc-base)[0]
    # The original loop counts 1000 to -1, then duplicates the manual LoadExec
    # path. Navigation resets it to 1000. Cross takes a separate manual path.
    expected={0x80010F8C:0x240203E8,0x80010FAC:0xAC22F064,
              0x800111BC:0x30624000,0x800111C0:0x10400038,
              0x800112C0:0x8C63F064,0x800112C8:0x2463FFFF,
              0x800112D0:0xAC23F064,0x800112D4:0x14620039}
    for pc,value in expected.items():assert word(pc)==value,hex(pc)
    body=data[2048+0xE50:2048+0x14A0]
    value=2166136261
    for byte in body:value=((value^byte)*16777619)&0xffffffff
    out=ROOT/'build-eu-seamless/generated/eu_boot_profile.inc'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(f'#define TOMBI_SELECTOR_HASH 0x{value:08X}u\n#define TOMBI_SELECTOR_START 0x80010E50u\n#define TOMBI_SELECTOR_END 0x800114A0u\n#define TOMBI_SELECTOR_BRANCH 0x800112D4u\n#define TOMBI_SELECTOR_TIMER 0x800AF064u\n')
    print('PASS: original EU selector timeout, manual confirmation and complete body guard',flush=True)


if __name__=='__main__':generate()
