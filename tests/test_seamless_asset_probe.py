"""Codec edge cases independent of original game assets."""
import importlib.util
from pathlib import Path
import struct
import unittest

spec = importlib.util.spec_from_file_location(
    "probe", Path(__file__).resolve().parents[1] / "tools" / "seamless_asset_probe.py")
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


def gam(size, body):
    return b"GAM\0" + struct.pack("<I", size) + body


class DecoderTests(unittest.TestCase):
    def test_literal(self):
        self.assertEqual(probe.decode_gam(gam(3, b"\0\0abc")), b"abc")

    def test_overlapping_reference(self):
        # Literal 'a', then distance 1, length 5; a forward copy grows itself.
        self.assertEqual(probe.decode_gam(gam(6, b"\x02\0a\x01\x05")), b"aaaaaa")

    def test_flag_rollover(self):
        data = gam(17, b"\0\0abcdefghijklmnop\0\0q")
        self.assertEqual(probe.decode_gam(data), b"abcdefghijklmnopq")

    def test_reject_previous_destination_dependency(self):
        for body in (b"\x01\0\x01\x03", b"\x01\0\x00\x03"):
            with self.assertRaisesRegex(ValueError, "prior RAM"):
                probe.decode_gam(gam(3, body))

    def test_reject_truncated_and_oversized_streams(self):
        for data in (b"GAM", gam(2, b"\0\0a"), gam(1, b"\x01\0\x01"),
                     gam(probe.MAX_OUTPUT + 1, b"\0\0")):
            with self.assertRaises(ValueError):
                probe.decode_gam(data)

    def test_preserve_final_token_tail(self):
        # Retail decoder finishes the token before checking the logical size.
        self.assertEqual(probe.decode_gam(gam(2, b"\x02\0a\x01\x03")), b"aaaa")


if __name__ == "__main__":
    unittest.main()
