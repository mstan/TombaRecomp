"""Audit every stock area/section and sound list against the real preflight.

Requires the player's resident pack (psxrecomp mod_resident format, e.g.
%LOCALAPPDATA%/TombaRecomp/seamless/scus94236-gam-v2-*.pack), the original
SCUS-94236 executable, Unicorn, and tests/seamless_request_fixture.c built as a
shared library. Runs the original MIPS queue builders, then the production C
request planner. This is resource coverage, not a gameplay, frame-pacing, or
audio-output test.
"""
import argparse
import ctypes
import hashlib
import json
from pathlib import Path
import re
import struct

from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_MIPS32, UC_MODE_LITTLE_ENDIAN
from unicorn import mips_const as reg

ROOT = Path(__file__).resolve().parent.parent


class TombaAsset(ctypes.Structure):
    """src/mods/tomba_seamless_assets.h"""
    _fields_ = [('lba', ctypes.c_uint32), ('size', ctypes.c_uint32),
                ('raw', ctypes.c_void_p), ('raw_len', ctypes.c_uint32),
                ('decoded', ctypes.c_void_p), ('decoded_len', ctypes.c_uint32),
                ('declared', ctypes.c_uint32), ('codec_state', ctypes.c_uint32)]


GAM_TAG = 0x444D4147  # 'GAMD', tomba_seamless_prepare.cpp


def read_pack(path):
    """psxrecomp runtime/src/mod_resident.cpp container, every hash checked."""
    data = path.read_bytes()
    if data[:8] != b'PSXRES01' or struct.unpack_from('<I', data, 8)[0] != 1:
        raise ValueError('Not a resident pack')
    nf, nd, nb = struct.unpack_from('<3I', data, 12)
    payload_size = struct.unpack_from('<Q', data, 56)[0]
    table = 64 + nf*20 + nd*28 + nb*48
    if hashlib.sha256(data[:table]).digest() != data[table:table+32]:
        raise ValueError('Resident pack table hash mismatch')
    payload = data[table+32:]
    if len(payload) != payload_size:
        raise ValueError('Resident pack size mismatch')
    files = [struct.unpack_from('<5I', data, 64+i*20) for i in range(nf)]
    derived = [struct.unpack_from('<7I', data, 64+nf*20+i*28) for i in range(nd)]
    blobs = []
    for i in range(nb):
        at = 64 + nf*20 + nd*28 + i*48
        offset, size = struct.unpack_from('<QI', data, at)
        blob = payload[offset:offset+size]
        if hashlib.sha256(blob).digest() != data[at+16:at+48]:
            raise ValueError('Resident pack blob hash mismatch')
        blobs.append(blob)
    return files, derived, blobs


def audit(exe_path, pack_path, library_path):
    lib = ctypes.CDLL(str(library_path.resolve()))
    lib.seamless_fixture_set_assets.argtypes = [ctypes.POINTER(TombaAsset), ctypes.c_uint]
    lib.seamless_fixture_plan.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                         ctypes.c_uint]
    catalog = (ROOT/'src/mods/tomba_seamless_catalog.inc').read_text()
    order = re.findall(r'\{"([^"]+)", (\d+), (\d+),', catalog)
    pack_files, pack_derived, blobs = read_pack(pack_path)
    if len(pack_files) != len(order):
        raise ValueError('Resident pack does not match the catalog')
    buffers = [ctypes.create_string_buffer(b, len(b)) for b in blobs]
    table = (TombaAsset * len(pack_files))()
    assets, files = {}, {}
    for i, ((lba, size, padded, _stock, blob), (name, _, _)) in enumerate(zip(pack_files, order)):
        table[i].lba, table[i].size, table[i].raw_len = lba, size, padded
        table[i].raw = ctypes.cast(buffers[blob], ctypes.c_void_p)
        assets[lba, size] = name
        files[name] = blobs[blob][:size]
    for file, tag, declared, state, length, _, blob in pack_derived:
        if tag == GAM_TAG:
            table[file].decoded = ctypes.cast(buffers[blob], ctypes.c_void_p)
            table[file].decoded_len, table[file].declared = length, declared
            table[file].codec_state = state
    lib.seamless_fixture_set_assets(table, len(pack_files))
    exe = exe_path.read_bytes()
    if exe != files['SCUS_942.36']:
        raise ValueError('Executable does not match the verified disc pack')
    uc = Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 | UC_MODE_LITTLE_ENDIAN)
    uc.mem_map(0, 2*1024*1024)
    uc.mem_map(0x1f800000, 4096)

    def read32(address):
        return struct.unpack('<I', uc.mem_read(address & 0x1fffffff, 4))[0]

    def read16(address):
        return struct.unpack('<H', uc.mem_read(address & 0x1fffffff, 2))[0]

    def write32(address, value):
        uc.mem_write(address & 0x1fffffff, struct.pack('<I', value))

    def reset(area=None):
        uc.mem_write(0, bytes(2*1024*1024))
        uc.mem_write(0x10000, exe[0x800:])
        uc.mem_write(0x1f800000, bytes(4096))
        if area is not None and area != 15:
            uc.mem_write(0x97fa8, files[f'SYS/LDAR{area:02d}.BIN'])
        write32(0x1f800298, 0x80141000)
        # Normal synchronous SPU DMA transfer setup. Custom callbacks remain
        # deliberately unsupported; runtime checks are not bypassed here.
        write32(0x80097c64, 0)
        write32(0x80097c80, 0)
        write32(0x80097c70, 3)

    def call(pc, *args):
        for register, arg in zip((reg.UC_MIPS_REG_A0, reg.UC_MIPS_REG_A1,
                                 reg.UC_MIPS_REG_A2), args):
            uc.reg_write(register, arg)
        uc.reg_write(reg.UC_MIPS_REG_SP, 0x801ff000)
        uc.reg_write(reg.UC_MIPS_REG_RA, 0x80000000)
        uc.emu_start(pc, 0x80000000, count=200000)
        if uc.reg_read(reg.UC_MIPS_REG_PC) != 0x80000000:
            raise ValueError(f'Original queue builder {pc:X} did not return')

    def preflight():
        ram = ctypes.create_string_buffer(bytes(uc.mem_read(0, 2*1024*1024)))
        scratch = ctypes.create_string_buffer(bytes(uc.mem_read(0x1f800000, 1024)))
        requests = []
        for i in range(read32(0x1f80029c)):
            desc = read32(0x8009e748+i*8)
            fid = read16(desc)
            m, s, f = uc.mem_read(0x791a0+fid*8, 3)
            bcd = lambda value: (value >> 4)*10+(value & 15)
            lba = (bcd(m)*60+bcd(s))*75+bcd(f)-150
            name = assets[lba, read32(0x800791a4+fid*8)]
            typ = uc.mem_read((desc & 0x1fffffff)+3, 1)[0]
            bank = read16(desc+14) if typ & 0xf0 == 0x90 else None
            requests.append(dict(file=name, descriptor=f'0x{desc:08X}',
                                 sound_bank=bank,
                                 accepted=bool(lib.seamless_fixture_plan(ram, scratch, i))))
        return requests

    reset()
    # Exact stock table boundaries: 75 bank configurations followed by loader
    # descriptors, and 52 pointers in the music/SFX list selector's table.
    assert 0x80077d50+75*8 == 0x80077fa8
    assert read32(0x80077fa8) == 0
    sound_lists = []
    for music in range(52):
        reset()
        pointer = read32(0x80078eb0+music*4)
        assert 0x80078348 <= pointer < 0x80078eb0
        call(0x800223a0, music)
        sound_lists.append(dict(list=music, requests=preflight()))

    areas = []
    for area in range(20):
        reset(area)
        count = read16(0x8007b294+area*2)  # Retail warp menu's section bounds.
        music_table = read32(0x8007716c+area*4)
        for section in range(count):
            reset(area)
            if area == 15:
                # This shared script section reuses allocation slot 3 from
                # the preceding scene (descriptor byte 0x83). Give it an
                # actual retail-built predecessor allocation, not zero RAM.
                uc.mem_write(0x97fa8, files['SYS/LDAR00.BIN'])
                call(0x80021cc8, 0, 0, 1)
                assert read32(0x1f8002b0) != 0
                write32(0x1f80029c, 0)
                write32(0x1f8002a0, 0)
            music = uc.mem_read((music_table & 0x1fffffff)+section, 1)[0]
            # Queue a music change as well as the full destination resource
            # list. Testing only LDAR files misses the reported regression.
            call(0x800223a0, music)
            call(0x80021cc8, area, section, 1)
            areas.append(dict(area=area, section=section, music_list=music,
                              predecessor='0/0 allocation' if area == 15 else None,
                              requests=preflight()))

    # Reject the first out-of-table index even when the rest of the request is
    # valid. Also prove ordinary busy/custom-callback protection still applies.
    reset()
    call(0x800223a0, 13)  # Haunted Mansion, sound bank 16.
    desc = read32(0x8009e748)
    uc.mem_write((desc & 0x1fffffff)+14, struct.pack('<H', 75))
    invalid_index_rejected = not preflight()[0]['accepted']
    reset()
    call(0x800223a0, 13)
    write32(0x80097c64, 0x80010000)
    callback_rejected = not preflight()[0]['accepted']
    failures = sum(not r['accepted'] for group in areas+sound_lists
                   for r in group['requests'])
    return dict(schema=1, scope='Stock resource preflight; not runtime route acceptance',
                area_count=20, area_sections=len(areas), sound_lists=len(sound_lists),
                requests=sum(len(g['requests']) for g in areas+sound_lists),
                failures=failures, invalid_index_rejected=invalid_index_rejected,
                custom_callback_rejected=callback_rejected,
                areas=areas, sounds=sound_lists)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe', type=Path, required=True)
    parser.add_argument('--pack', type=Path, required=True)
    parser.add_argument('--fixture', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.exe, args.pack, args.fixture)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('areas', 'sounds')}))
    raise SystemExit(bool(result['failures']) or not result['invalid_index_rejected']
                     or not result['custom_callback_rejected'])
