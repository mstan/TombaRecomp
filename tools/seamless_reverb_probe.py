"""Compare the compiled native reverb transfer with the original MIPS driver.

Requires the owner's SCUS-94236 executable and Unicorn 2.1.4. The original
76400 routine executes unchanged, including allocation checks and chunk loops.
Only its low-level DMA and WaitEvent boundaries are modeled as completed
transfers. This proves bytes, bounds and transfer state, not audible timing.
"""
import argparse
import ctypes as ct
import hashlib
from pathlib import Path
import struct


def verify(exe_path, native_path):
    from unicorn import Uc, UC_ARCH_MIPS, UC_MODE_MIPS32, UC_MODE_LITTLE_ENDIAN, UC_HOOK_CODE
    from unicorn import mips_const as reg
    exe = exe_path.read_bytes()
    expected = 'c45cd788df40a540d8641dc9682007c80e6ab8a4bcdd0e4a4e2c14c5108aa10b'
    if hashlib.sha256(exe).hexdigest() != expected:
        raise ValueError('Unsupported original executable')
    address, size = struct.unpack_from('<II', exe, 0x18)
    lib = ct.CDLL(str(native_path.resolve()))
    native = lib.seamless_reverb_fixture
    native.argtypes = [ct.c_uint32, ct.POINTER(ct.c_uint8), ct.POINTER(ct.c_uint8), ct.POINTER(ct.c_uint32)]
    native.restype = None
    cases = 0
    for mode in range(10):
        for pattern in (0, 1):
            for fill in (0xA5, 0x5A):
                uc = Uc(UC_ARCH_MIPS, UC_MODE_MIPS32 | UC_MODE_LITTLE_ENDIAN)
                uc.mem_map(0, 2 * 1024 * 1024)
                uc.mem_write(address & 0x1FFFFFFF, exe[0x800:0x800+size])
                def read(a):
                    return int.from_bytes(uc.mem_read(a & 0x1FFFFFFF, 4), 'little')
                def write(a, v):
                    uc.mem_write(a & 0x1FFFFFFF, struct.pack('<I', v))
                scratch = bytes(1024) if not pattern else bytes((i * 17 + 3) & 255 for i in range(1024))
                uc.mem_write(0x97840, scratch)
                initial = [0xABCD3210, 1, 0x11223344, 55, 0x3210, 0xC001]
                locations = [0x80097C60, 0x80097C98, 0x80097C9C, 0x80097CA0]
                for a, v in zip(locations, initial):
                    write(a, v)
                write(0x80097C70, 3)
                write(0x80097C64, 0)  # synchronous DMA transfer mode
                write(0x80097C80, 0)  # no custom completion callback
                write(0x80097CAC, 0)  # no conflicting allocated block
                sound = bytearray([fill]) * 0x80000
                hardware = initial[4:]
                chunks = []
                def boundary(machine, pc, instruction_size, userdata):
                    if pc == 0x80074834:
                        command = machine.reg_read(reg.UC_MIPS_REG_A0)
                        a1 = machine.reg_read(reg.UC_MIPS_REG_A1)
                        a2 = machine.reg_read(reg.UC_MIPS_REG_A2)
                        if command == 2:
                            write(0x80097C60, (read(0x80097C60) & 0xFFFF0000) | (a1 >> 3))
                            hardware[0] = a1 >> 3
                        elif command == 1:
                            write(0x80097C98, 0)
                            hardware[1] = (hardware[1] & ~0x30) | 0x20
                        elif command == 3:
                            count = (a2 + 63) & ~63
                            begin = hardware[0] * 8
                            data = uc.mem_read(a1 & 0x1FFFFFFF, count)
                            for i, byte in enumerate(data):
                                sound[(begin+i) & 0x7FFFF] = byte
                            write(0x80097C9C, a1)
                            write(0x80097CA0, count // 64)
                            hardware[1] &= ~0x30
                            chunks.append((begin, count))
                        else:
                            raise AssertionError(f'Unexpected transfer command {command}')
                        machine.reg_write(reg.UC_MIPS_REG_V0, 0)
                        machine.reg_write(reg.UC_MIPS_REG_PC, machine.reg_read(reg.UC_MIPS_REG_RA))
                    elif pc == 0x8007659C:
                        machine.reg_write(reg.UC_MIPS_REG_V0, 1)  # completed transfer event
                        machine.reg_write(reg.UC_MIPS_REG_PC, machine.reg_read(reg.UC_MIPS_REG_RA))
                uc.hook_add(UC_HOOK_CODE, boundary, begin=0x80074834, end=0x8007659C)
                uc.reg_write(reg.UC_MIPS_REG_A0, mode)
                uc.reg_write(reg.UC_MIPS_REG_SP, 0x801FF000)
                uc.reg_write(reg.UC_MIPS_REG_RA, 0x80000000)
                uc.emu_start(0x80076400, 0x80000000, timeout=5_000_000, count=2_000_000)
                assert uc.reg_read(reg.UC_MIPS_REG_PC) == 0x80000000
                assert uc.reg_read(reg.UC_MIPS_REG_V0) == 0 and chunks
                begin = chunks[0][0]  # original routine decides the extent
                native_sound = (ct.c_uint8 * 0x80000)(*([fill] * 0x80000))
                native_source = (ct.c_uint8 * 1024).from_buffer_copy(scratch)
                native_state = (ct.c_uint32 * 6)(*initial)
                native(begin, native_sound, native_source, native_state)
                assert bytes(native_sound) == bytes(sound), (mode, pattern, fill, 'SPU bytes')
                assert list(native_state) == [read(a) for a in locations] + hardware, (mode, 'transfer state')
                cases += 1
    print(f'{cases} original-MIPS/native comparisons passed: all 10 reverb modes, zero/patterned source, two poisoned destinations')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--exe', type=Path, required=True)
    p.add_argument('--native-library', type=Path, required=True)
    args = p.parse_args()
    verify(args.exe, args.native_library)
